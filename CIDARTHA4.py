import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from ipaddress import ip_network
from threading import Lock, RLock
from functools import lru_cache
from typing import Optional, Tuple, Dict

import msgpack
from config import CIDARTHAConfig, get_default_config

# Predefine bit masks
MASKS = [(0xFF << (8 - i)) & 0xFF for i in range(1, 9)]

# Custom logger setup
logger = logging.getLogger("CIDARTHA")
logger.setLevel(logging.INFO)

# Optimized IP to bytes conversion - C-level heavy lifting
_inet_pton = socket.inet_pton
_AF_INET = socket.AF_INET
_AF_INET6 = socket.AF_INET6


def _ip_to_bytes_cached_impl(ip: str) -> bytes:
    """Cached IP string to bytes conversion (implementation)."""
    try:
        return _inet_pton(_AF_INET, ip)
    except OSError:
        try:
            return _inet_pton(_AF_INET6, ip)
        except OSError:
            raise ValueError(f"Invalid IP: {ip}")


# Default global cache with standard size
_ip_to_bytes_cached = lru_cache(maxsize=8192)(_ip_to_bytes_cached_impl)


def configure_global_ip_cache(cache_size: int = 8192):
    """
    Configure the global IP to bytes cache size.
    
    This function allows users to adjust the size of the global LRU cache used
    for IP string to bytes conversion. This cache is shared across all CIDARTHA
    instances.
    
    Args:
        cache_size: Maximum number of IP addresses to cache (default: 8192)
    
    Example:
        >>> from CIDARTHA4 import configure_global_ip_cache
        >>> configure_global_ip_cache(16384)  # Double the cache size
    
    Note:
        This should be called before creating CIDARTHA instances for best effect.
        Calling this will clear any existing cached values.
    """
    global _ip_to_bytes_cached
    _ip_to_bytes_cached = lru_cache(maxsize=cache_size)(_ip_to_bytes_cached_impl)


def _ip_to_bytes(ip) -> bytes:
    """CPython-optimized IP → bytes conversion."""
    t = type(ip)

    if t is bytes:
        return ip

    if t is str:
        return _ip_to_bytes_cached(ip)

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
    def __init__(self, config=None):
        """
        Initialize CIDARTHA with optional configuration.
        
        Args:
            config: Optional CIDARTHAConfig instance for customizing behavior.
                   If None, uses the global default configuration.
        
        Examples:
            >>> # Use default configuration
            >>> fw = CIDARTHA()
            
            >>> # Use custom configuration
            >>> from config import CIDARTHAConfig
            >>> config = CIDARTHAConfig(check_cache_size=8192)
            >>> fw = CIDARTHA(config=config)
        """
        self.root = CIDARTHANode()
        self._lock = RLock()  # Reentrant lock for thread safety
        
        # Get configuration
        if config is None:
            config = get_default_config()
        self.config = config
        
        # Set logger level if config is provided
        if self.config is not None:
            logger.setLevel(self.config.log_level)
        
        # Setup caches with configuration
        self._setup_caches()
    
    def _setup_caches(self):
        """Setup LRU caches with configured sizes."""
        if self.config is not None:
            # Wrap methods with configured cache sizes
            self._cached_ip_network = lru_cache(maxsize=self.config.ip_network_cache_size)(
                self._cached_ip_network_impl
            )
            self.check = lru_cache(maxsize=self.config.check_cache_size)(
                self._check_impl
            )
        else:
            # Use default caching for backward compatibility
            self._cached_ip_network = lru_cache(maxsize=4096)(
                self._cached_ip_network_impl
            )
            self.check = lru_cache(maxsize=4096)(
                self._check_impl
            )

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_lock']
        # Remove cached methods which can't be pickled
        if 'check' in state:
            del state['check']
        if '_cached_ip_network' in state:
            del state['_cached_ip_network']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = RLock()
        # Recreate cached methods using helper
        self._setup_caches()

    def dump(self) -> bytes:
        """Dump trie to compact msgpack bytes."""
        logger.info("Starting serialization.")
        root_tuple = self.root.to_compact_tuple()
        flat_data = {'root': root_tuple}
        logger.info("Serialization complete.")
        return msgpack.packb(flat_data, use_bin_type=True)

    @staticmethod
    def load(serialized_data: bytes, config=None) -> "CIDARTHA":
        """
        Load trie from msgpack bytes.
        
        Args:
            serialized_data: Serialized trie data
            config: Optional CIDARTHAConfig instance for the loaded instance
        """
        logger.info("Starting deserialization.")
        flat_data = msgpack.unpackb(serialized_data, raw=False, strict_map_key=False)
        cidartha = CIDARTHA(config=config)
        cidartha.root = CIDARTHANode.from_compact_tuple(flat_data['root'])
        logger.info("Deserialization complete.")
        return cidartha

    def _cached_ip_network_impl(self, input_data: str):
        """Cache ip_network calls (implementation)."""
        return ip_network(input_data, strict=False)

    def insert(self, input_data: str, _clear_cache=True):
        """Thread-safe CIDR insertion."""
        with self._lock:
            try:
                network = self._cached_ip_network(input_data)
                self._insert_cidr(network)
                # Clear cache after modification (can be disabled for batch operations)
                if _clear_cache:
                    self.check.cache_clear()
                    _ip_to_bytes_cached.cache_clear()
            except ValueError as e:
                logger.error(f"Invalid IP or CIDR range: {input_data} - {e}")
                raise

    def batch_insert(self, entries):
        """Batch insert with optimized logging and cache handling."""
        total = len(entries)
        if not total:
            logger.info("No entries to insert.")
            return

        # Use configurable log interval
        if self.config is not None:
            log_every = max(1, int(total * self.config.batch_insert_log_interval))
        else:
            log_every = max(1, total // 20)  # Default: 5%
        next_log = log_every

        logger.info(f"Starting batch insert of {total} entries.")
        
        # Process entries in batch with lock held for better performance
        with self._lock:
            for i, entry in enumerate(entries, 1):
                if entry := entry.strip():
                    try:
                        network = self._cached_ip_network(entry)
                        self._insert_cidr(network)
                        if i == next_log or i == total:
                            logger.info(f"Inserted {i}/{total} ({100 * i / total:.1f}%)")
                            next_log += log_every
                    except ValueError as e:
                        logger.error(f"Failed to insert {entry}: {e}")
            
            # Clear caches once after all inserts
            self.check.cache_clear()
            _ip_to_bytes_cached.cache_clear()
        
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
            # Calculate the range of byte values that match this prefix
            base_byte = addr[full_bytes] & masks[rem_bits - 1]
            # Number of bits that are variable in this byte
            variable_bits = 8 - rem_bits
            # Number of different values possible
            num_values = 1 << variable_bits
            
            # Pre-allocate children dict if needed for efficiency
            if node._children is None:
                node._children = {}
            children = node._children
            
            # Create nodes for all byte values in the range
            for offset in range(num_values):
                b = base_byte | offset
                nxt = children.get(b)
                if nxt is None:
                    nxt = NodeCtor()
                    children[b] = nxt
                
                # Mark this node as end
                mark_end(nxt, network)
        else:
            # Full byte prefix - mark this node as end
            mark_end(node, network)

    def _check_impl(self, ip) -> bool:
        """Optimized IP lookup with direct dict access (implementation)."""
        ip_bytes = _ip_to_bytes(ip)
        
        root = self.root
        if root.is_end:
            return True
        
        node = root
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
                # Clear caches after modification
                self.check.cache_clear()
                _ip_to_bytes_cached.cache_clear()
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
            # Clear caches after modification
            self.check.cache_clear()
            _ip_to_bytes_cached.cache_clear()

    def clear(self):
        """Thread-safe clear."""
        with self._lock:
            self.root = CIDARTHANode()
            # Clear caches after modification
            self.check.cache_clear()
            _ip_to_bytes_cached.cache_clear()

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