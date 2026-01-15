import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from ipaddress import ip_network
from threading import Lock, RLock
from functools import lru_cache
from typing import Optional, Tuple, Dict

import msgpack

# Predefine bit masks
MASKS = [(0xFF << (8 - i)) & 0xFF for i in range(1, 9)]

# Custom logger setup
logger = logging.getLogger("CIDARTHA")
logger.setLevel(logging.INFO)

# Optimized IP to bytes conversion - C-level heavy lifting
_inet_pton = socket.inet_pton
_AF_INET = socket.AF_INET
_AF_INET6 = socket.AF_INET6


def _ip_to_bytes(ip) -> bytes:
    """CPython-optimized IP → bytes conversion."""
    t = type(ip)

    if t is bytes:
        return ip

    if t is str:
        try:
            return _inet_pton(_AF_INET, ip)
        except OSError:
            try:
                return _inet_pton(_AF_INET6, ip)
            except OSError:
                raise ValueError(f"Invalid IP: {ip}")

    if t is int:
        return b"\x00" if ip == 0 else ip.to_bytes((ip.bit_length() + 7) >> 3, "big")

    try:
        return ip.packed
    except AttributeError:
        pass

    raise ValueError(f"Unsupported type: {t.__name__}")


@dataclass(slots=True)
class CIDARTHANode:
    """Memory-optimized trie node."""
    is_end: bool = False
    range_start: Optional[bytes] = None
    range_end: Optional[bytes] = None
    _children: Optional[Dict[int, "CIDARTHANode"]] = field(default=None, repr=False)

    # ---- Minimal dict-like interface ----
    def get(self, k, default=None):
        return self._children.get(k, default) if self._children else default

    def __setitem__(self, k, v):
        if self._children is None:
            self._children = {}
        self._children[k] = v

    def __delitem__(self, k):
        if self._children is None:
            raise KeyError(k)
        del self._children[k]
        if not self._children:
            self._children = None

    def items(self):
        return self._children.items() if self._children else iter(())

    def __len__(self):
        return len(self._children) if self._children else 0

    # ---- Compact tuple serialization ----
    def to_compact_tuple(self) -> Tuple[bool, Optional[bytes], Optional[bytes], Optional[Dict]]:
        """Serialize to (is_end, start, end, children_dict) format."""
        children = None
        if self._children:
            children = {k: v.to_compact_tuple() for k, v in self._children.items()}
        return (self.is_end, self.range_start, self.range_end, children)

    @staticmethod
    def from_compact_tuple(data: Tuple) -> "CIDARTHANode":
        """Deserialize from compact tuple format."""
        is_end, start, end, children_dict = data
        node = CIDARTHANode(is_end=is_end, range_start=start, range_end=end)

        if children_dict:
            # Direct assignment to avoid __setitem__ overhead during construction
            node._children = {
                k: CIDARTHANode.from_compact_tuple(v) for k, v in children_dict.items()
            }

        return node


class CIDARTHA:
    def __init__(self, cache_size: int = 4096):
        """
        Initialize CIDARTHA with configurable cache size.
        
        Args:
            cache_size: Maximum number of IP lookups to cache (default: 4096).
                       Set to 0 to disable caching. Larger values use more memory
                       but can improve performance for workloads with many distinct IPs.
        """
        self.root = CIDARTHANode()
        self._lock = RLock()  # Reentrant lock for thread safety
        self._cache_size = cache_size
        
        # Dynamically create check method with configurable cache size
        if cache_size > 0:
            # Create a cached version of _check_impl
            cached_check = lru_cache(maxsize=cache_size)(self._check_impl)
            # Store reference so we can access cache_info() and cache_clear()
            self._check_cached = cached_check
            self.check = cached_check
        else:
            # No caching
            self.check = self._check_impl
            self._check_cached = None

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_lock']
        # Don't pickle the check method or cache, they will be recreated
        if 'check' in state:
            del state['check']
        if '_check_cached' in state:
            del state['_check_cached']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = RLock()
        # Recreate check method with caching
        cache_size = state.get('_cache_size', 4096)
        if cache_size > 0:
            cached_check = lru_cache(maxsize=cache_size)(self._check_impl)
            self._check_cached = cached_check
            self.check = cached_check
        else:
            self.check = self._check_impl
            self._check_cached = None

    def dump(self) -> bytes:
        """Dump trie to compact msgpack bytes."""
        logger.info("Starting serialization.")
        root_tuple = self.root.to_compact_tuple()
        flat_data = {'root': root_tuple, 'cache_size': self._cache_size}
        logger.info("Serialization complete.")
        return msgpack.packb(flat_data, use_bin_type=True)

    @staticmethod
    def load(serialized_data: bytes) -> "CIDARTHA":
        """Load trie from msgpack bytes."""
        logger.info("Starting deserialization.")
        flat_data = msgpack.unpackb(serialized_data, raw=False, strict_map_key=False)
        cache_size = flat_data.get('cache_size', 4096)
        cidartha = CIDARTHA(cache_size=cache_size)
        cidartha.root = CIDARTHANode.from_compact_tuple(flat_data['root'])
        logger.info("Deserialization complete.")
        return cidartha

    @lru_cache(maxsize=4096)
    def _cached_ip_network(self, input_data: str):
        """Cache ip_network calls."""
        return ip_network(input_data, strict=False)

    def insert(self, input_data: str):
        """Thread-safe CIDR insertion."""
        with self._lock:
            try:
                network = self._cached_ip_network(input_data)
                self._insert_cidr(network)
            except ValueError as e:
                logger.error(f"Invalid IP or CIDR range: {input_data} - {e}")
                raise

    def batch_insert(self, entries):
        """Batch insert with optimized logging."""
        total = len(entries)
        if not total:
            logger.info("No entries to insert.")
            return

        log_every = max(1, total // 20)
        next_log = log_every

        logger.info(f"Starting batch insert of {total} entries.")
        for i, entry in enumerate(entries, 1):
            if entry := entry.strip():
                try:
                    self.insert(entry)
                    if i == next_log or i == total:
                        logger.info(f"Inserted {i}/{total} ({100 * i / total:.1f}%)")
                        next_log += log_every
                except ValueError as e:
                    logger.error(f"Failed to insert {entry}: {e}")

        logger.info("Batch insert complete.")

    def _insert_cidr(self, network):
        """Internal CIDR insertion (lock must be held)."""
        # /0 = wildcard (match everything)
        if network.prefixlen == 0:
            self._set_root_as_wildcard(network)
            return

        addr = network.network_address.packed
        prefix_len = network.prefixlen
        node = self.root

        full_bytes = prefix_len >> 3
        rem_bits = prefix_len & 7

        # Hot-path locals (cuts attribute/global lookups in the loop)
        NodeCtor = CIDARTHANode
        mark_end = self._mark_as_end_node
        masks = MASKS

        # Traverse full bytes
        for i in range(full_bytes):
            b = addr[i]
            children = node._children
            if children is None:
                nxt = NodeCtor()
                node[b] = nxt  # creates children dict once (via __setitem__)
            else:
                nxt = children.get(b)
                if nxt is None:
                    nxt = NodeCtor()
                    children[b] = nxt
            node = nxt

        # Handle partial byte
        if rem_bits:
            b = addr[full_bytes] & masks[rem_bits - 1]
            children = node._children
            if children is None:
                nxt = NodeCtor()
                node[b] = nxt
            else:
                nxt = children.get(b)
                if nxt is None:
                    nxt = NodeCtor()
                    children[b] = nxt
            node = nxt

        mark_end(node, network)

    def _check_impl(self, ip) -> bool:
        """Optimized IP lookup with direct dict access (used for caching)."""
        ip_bytes = _ip_to_bytes(ip)

        if self.root.is_end:
            return True

        node = self.root
        for byte in ip_bytes:
            children = node._children
            if children is None:
                return False

            node = children.get(byte)
            if node is None:
                return False
            if node.is_end:
                return True

        return False

    def remove(self, cidr: str):
        """Thread-safe CIDR removal."""
        with self._lock:
            try:
                network = self._cached_ip_network(cidr)
            except ValueError as e:
                logger.error(f"Invalid CIDR range: {cidr} - {e}")
                raise

            if network.prefixlen == 0:
                self.root = CIDARTHANode()  # Clear directly to avoid deadlock
                # Clear cache when removing wildcard
                if self._check_cached and hasattr(self._check_cached, 'cache_clear'):
                    self._check_cached.cache_clear()
                return

            path = self._traverse_path(network.network_address.packed, network.prefixlen)
            if not path:
                return

            parent, final_byte = path[-1]
            children = parent._children
            if children is None:
                return

            node = children.get(final_byte)
            if node is None:
                return

            self._remove_end_node(node)
            self._prune_empty_nodes(path)
            
            # Clear cache after removal
            if self._check_cached and hasattr(self._check_cached, 'cache_clear'):
                self._check_cached.cache_clear()

    def clear(self):
        """Thread-safe clear."""
        with self._lock:
            self.root = CIDARTHANode()
            # Clear the cache after clearing the trie
            if self._check_cached and hasattr(self._check_cached, 'cache_clear'):
                self._check_cached.cache_clear()

    def _traverse_path(self, address_bytes, prefix_len=None):
        """Return list of (parent_node, byte_to_child) for traversal path."""
        if prefix_len is None:
            prefix_len = len(address_bytes) << 3

        path = []
        node = self.root
        full_bytes = prefix_len >> 3
        remaining_bits = prefix_len & 7

        for i in range(full_bytes):
            byte = address_bytes[i]
            path.append((node, byte))

            children = node._children
            if children is None:
                return path

            next_node = children.get(byte)
            if next_node is None:
                return path

            node = next_node

        if remaining_bits:
            byte = address_bytes[full_bytes] & MASKS[remaining_bits - 1]
            path.append((node, byte))

        return path

    def _set_root_as_wildcard(self, network):
        self.root.is_end = True
        self.root.range_start = network.network_address.packed
        self.root.range_end = network.broadcast_address.packed


   ###
    # Helper methods for node manipulation
    ###
    @staticmethod
    def _mark_as_end_node(node, network):
        node.is_end = True
        node.range_start = network.network_address.packed
        node.range_end = network.broadcast_address.packed

    @staticmethod
    def _remove_end_node(node):
        node.is_end = False
        node.range_start = None
        node.range_end = None

    @staticmethod
    def _prune_empty_nodes(path):
        for parent, byte in reversed(path):
            children = parent._children
            if children is None:
                continue

            node = children.get(byte)
            if node is None:
                continue

            if not node._children and not node.is_end:
                del children[byte]
                if not children:
                    parent._children = None
            else:
                break