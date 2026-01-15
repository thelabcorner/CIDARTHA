import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from ipaddress import ip_network
from threading import Lock, RLock
from functools import lru_cache
from typing import Optional, Tuple, Dict, Literal

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


@dataclass
class CIDARTHAConfig:
    """Configuration for CIDARTHA caching behavior.
    
    Attributes:
        cache_strategy: Caching strategy to use:
            - "none": No caching (best for workloads where each IP is unique)
            - "simple": Single LRU cache, no normalization (fastest, but separate entries for str vs bytes)
            - "normalized": Single LRU cache with pre-normalization to bytes (consistent cache keys, slight overhead)
            - "dual": Two LRU caches - one for string->bytes, one for bytes->result (balanced approach)
        cache_size: Maximum number of entries in each cache (default: 4096)
    """
    cache_strategy: Literal["none", "simple", "normalized", "dual"] = "normalized"
    cache_size: int = 4096

    def __post_init__(self):
        if self.cache_strategy not in ("none", "simple", "normalized", "dual"):
            raise ValueError(f"Invalid cache_strategy: {self.cache_strategy}")
        if self.cache_size < 0:
            raise ValueError(f"cache_size must be non-negative: {self.cache_size}")


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
    def __init__(self, config: Optional[CIDARTHAConfig] = None):
        """Initialize CIDARTHA with optional configuration.
        
        Args:
            config: CIDARTHAConfig instance. If None, uses default configuration.
        """
        self.root = CIDARTHANode()
        self._lock = RLock()  # Reentrant lock for thread safety
        self.config = config if config is not None else CIDARTHAConfig()
        
        # Initialize caching based on strategy
        self._setup_caching()

    def _setup_caching(self):
        """Setup caching methods based on configuration."""
        strategy = self.config.cache_strategy
        cache_size = self.config.cache_size
        
        if strategy == "none":
            # No caching - direct lookup
            self._check_impl = self._check_no_cache
            self._normalize_cache = None
            
        elif strategy == "simple":
            # Simple LRU cache - no normalization, accepts any input type
            if cache_size > 0:
                self._check_impl = lru_cache(maxsize=cache_size)(self._check_no_cache)
            else:
                self._check_impl = self._check_no_cache
            self._normalize_cache = None
            
        elif strategy == "normalized":
            # Normalized caching - always convert to bytes first
            if cache_size > 0:
                self._check_bytes_cached = lru_cache(maxsize=cache_size)(self._check_bytes_impl)
            else:
                self._check_bytes_cached = self._check_bytes_impl
            self._check_impl = self._check_normalized
            self._normalize_cache = None
            
        elif strategy == "dual":
            # Dual cache - separate cache for normalization and lookup
            if cache_size > 0:
                self._normalize_cache = lru_cache(maxsize=cache_size)(_ip_to_bytes)
                self._check_bytes_cached = lru_cache(maxsize=cache_size)(self._check_bytes_impl)
            else:
                self._normalize_cache = _ip_to_bytes
                self._check_bytes_cached = self._check_bytes_impl
            self._check_impl = self._check_dual
        
        else:
            raise ValueError(f"Unknown cache strategy: {strategy}")

    def _check_no_cache(self, ip) -> bool:
        """Direct check without any caching."""
        ip_bytes = _ip_to_bytes(ip)
        return self._check_bytes_impl(ip_bytes)

    def _check_normalized(self, ip) -> bool:
        """Check with normalized caching (always convert to bytes first)."""
        ip_bytes = _ip_to_bytes(ip)
        return self._check_bytes_cached(ip_bytes)

    def _check_dual(self, ip) -> bool:
        """Check with dual caching (separate normalization and lookup caches)."""
        ip_bytes = self._normalize_cache(ip)
        return self._check_bytes_cached(ip_bytes)

    def _check_bytes_impl(self, ip_bytes: bytes) -> bool:
        """Core lookup implementation that operates on bytes."""
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

    def check(self, ip) -> bool:
        """Optimized IP lookup with configurable caching.
        
        Args:
            ip: IP address as string, bytes, int, or IPv4Address/IPv6Address object
            
        Returns:
            bool: True if IP matches a stored CIDR block, False otherwise
        """
        return self._check_impl(ip)

    def get_cache_info(self) -> Dict:
        """Get cache statistics for the configured caching strategy.
        
        Returns:
            dict: Cache statistics including strategy, hits, misses, size, etc.
        """
        result = {
            "strategy": self.config.cache_strategy,
            "cache_size": self.config.cache_size,
        }
        
        if self.config.cache_strategy == "none":
            result["status"] = "no_cache"
            
        elif self.config.cache_strategy == "simple":
            if self.config.cache_size > 0:
                info = self._check_impl.cache_info()
                result.update({
                    "hits": info.hits,
                    "misses": info.misses,
                    "maxsize": info.maxsize,
                    "currsize": info.currsize,
                })
            else:
                result["status"] = "cache_disabled"
                
        elif self.config.cache_strategy == "normalized":
            if self.config.cache_size > 0:
                info = self._check_bytes_cached.cache_info()
                result.update({
                    "hits": info.hits,
                    "misses": info.misses,
                    "maxsize": info.maxsize,
                    "currsize": info.currsize,
                })
            else:
                result["status"] = "cache_disabled"
                
        elif self.config.cache_strategy == "dual":
            if self.config.cache_size > 0:
                norm_info = self._normalize_cache.cache_info()
                check_info = self._check_bytes_cached.cache_info()
                result.update({
                    "normalize_cache": {
                        "hits": norm_info.hits,
                        "misses": norm_info.misses,
                        "maxsize": norm_info.maxsize,
                        "currsize": norm_info.currsize,
                    },
                    "lookup_cache": {
                        "hits": check_info.hits,
                        "misses": check_info.misses,
                        "maxsize": check_info.maxsize,
                        "currsize": check_info.currsize,
                    },
                })
            else:
                result["status"] = "cache_disabled"
        
        return result

    def clear_cache(self):
        """Clear all caches."""
        if self.config.cache_strategy == "simple" and self.config.cache_size > 0:
            self._check_impl.cache_clear()
        elif self.config.cache_strategy == "normalized" and self.config.cache_size > 0:
            self._check_bytes_cached.cache_clear()
        elif self.config.cache_strategy == "dual" and self.config.cache_size > 0:
            self._normalize_cache.cache_clear()
            self._check_bytes_cached.cache_clear()

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove non-serializable items
        del state['_lock']
        # Remove cached methods (they'll be recreated on load)
        if '_check_impl' in state:
            del state['_check_impl']
        if '_check_bytes_cached' in state:
            del state['_check_bytes_cached']
        if '_normalize_cache' in state:
            del state['_normalize_cache']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = RLock()
        # Recreate caching
        self._setup_caching()

    def dump(self) -> bytes:
        """Dump trie to compact msgpack bytes."""
        logger.info("Starting serialization.")
        root_tuple = self.root.to_compact_tuple()
        flat_data = {
            'root': root_tuple,
            'config': {
                'cache_strategy': self.config.cache_strategy,
                'cache_size': self.config.cache_size,
            }
        }
        logger.info("Serialization complete.")
        return msgpack.packb(flat_data, use_bin_type=True)

    @staticmethod
    def load(serialized_data: bytes) -> "CIDARTHA":
        """Load trie from msgpack bytes."""
        logger.info("Starting deserialization.")
        flat_data = msgpack.unpackb(serialized_data, raw=False, strict_map_key=False)
        
        # Load config if present (backward compatibility)
        if 'config' in flat_data:
            config = CIDARTHAConfig(
                cache_strategy=flat_data['config']['cache_strategy'],
                cache_size=flat_data['config']['cache_size']
            )
        else:
            config = CIDARTHAConfig()
        
        cidartha = CIDARTHA(config=config)
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

    def clear(self):
        """Thread-safe clear."""
        with self._lock:
            self.root = CIDARTHANode()

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
