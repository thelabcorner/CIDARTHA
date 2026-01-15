# CIDARTHA5

**C**IDR **I**P **D**ata **A**ggregation **R**outine **T**rie with **H**igh-performance **A**rchitecture - Version 5

A production-ready, high-performance, thread-safe IP/CIDR firewall trie data structure for Python. CIDARTHA5 builds upon CIDARTHA4 with critical improvements for production workloads.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What's New in CIDARTHA5

### 🎯 Key Improvements Over CIDARTHA4

1. **🔧 Fixed Cache Argument-Sensitivity Issue**
   - CIDARTHA4: Different input types (strings, bytes, IP objects) create separate cache entries
   - CIDARTHA5: All input types are normalized to bytes before caching, maximizing cache hit rate
   - **Result**: Up to 66.7% cache hit rate vs 0.9% in mixed workloads (14.4% faster)

2. **⚙️ Configurable Cache Size**
   - CIDARTHA4: Hardcoded 4096 entry cache size
   - CIDARTHA5: Configurable cache size via constructor parameter
   - **Result**: Users can tune cache size for their workload (e.g., 8192 for high-volume systems)

3. **📊 Production-Ready Configuration**
   - Cache size can be adjusted based on expected distinct IP count
   - Cache can be disabled entirely (cache_size=0) for deterministic performance
   - Configuration is preserved during serialization/deserialization

### Performance Benchmarks

Based on comprehensive benchmarks comparing CIDARTHA4 vs CIDARTHA5:

| Scenario | CIDARTHA4 | CIDARTHA5 | Improvement |
|----------|-----------|-----------|-------------|
| Mixed input types (string/bytes/objects) | 0.9% hit rate | 66.7% hit rate | **14.4% faster** |
| Input type switching | 0.000311s | 0.000259s | **21.9% faster** |
| Insert operations | 0.005401s | 0.004932s | **8.7% faster** |
| Large workload (8000+ IPs) | Fixed 4096 | Configurable 8192 | **1.6% faster** |

## Overview

CIDARTHA5 implements a specialized trie (prefix tree) data structure optimized for IP address and CIDR block operations. It's designed for applications that need fast IP filtering, firewall rules, IP allowlists/blocklists, or network range lookups.

### Key Features

- **⚡ High Performance**: O(k) insertion and lookup time complexity (k = IP address bits)
- **🔒 Thread-Safe**: Built with reentrant locks for concurrent operations
- **💾 Memory Optimized**: Binary trie structure with minimal dictionary overhead
- **📦 Serialization**: Compact msgpack-based persistence with efficient storage
- **🚀 Smart Caching**: Normalized LRU caching with configurable size
- **🔄 Full CRUD Operations**: Insert, remove, check, and clear with batch support
- **🌐 IPv4/IPv6 Support**: Handles both IPv4 and IPv6 addresses seamlessly
- **⚙️ C-Level Optimization**: Uses CPython's socket module for fast conversions
- **🎛️ Production-Ready**: Configurable for different workload patterns

## Installation

### Requirements

```bash
pip install msgpack
```

### Basic Setup

Simply include `CIDARTHA5.py` in your project:

```python
from CIDARTHA5 import CIDARTHA
```

## Quick Start

```python
from CIDARTHA5 import CIDARTHA

# Create a new CIDARTHA instance with default cache (4096)
firewall = CIDARTHA()

# Or create with custom cache size for high-volume workloads
firewall = CIDARTHA(cache_size=8192)

# Insert CIDR blocks
firewall.insert("192.168.1.0/24")
firewall.insert("10.0.0.0/8")
firewall.insert("2001:db8::/32")  # IPv6 support

# Check if an IP is in the firewall - works with any input type!
if firewall.check("192.168.1.100"):  # string
    print("IP is blocked!")

if firewall.check(b"\xc0\xa8\x01\x64"):  # bytes
    print("IP is blocked!")

if firewall.check(ipaddress.IPv4Address("192.168.1.100")):  # IP object
    print("IP is blocked!")
```

## Usage Examples

### Basic Operations

```python
from CIDARTHA5 import CIDARTHA

# Initialize with custom cache size
firewall = CIDARTHA(cache_size=8192)

# Insert individual CIDR blocks
firewall.insert("172.16.0.0/12")
firewall.insert("192.168.0.0/16")

# Check IP addresses
firewall.check("172.16.50.1")     # Returns True
firewall.check("192.168.1.1")     # Returns True
firewall.check("8.8.8.8")         # Returns False

# Remove a CIDR block
firewall.remove("172.16.0.0/12")
firewall.check("172.16.50.1")     # Now returns False

# Clear all entries
firewall.clear()
```

### Configuring Cache for Different Workloads

```python
# High-volume workload with >4096 distinct IPs
high_volume_fw = CIDARTHA(cache_size=16384)

# Default cache for typical workloads
standard_fw = CIDARTHA()  # cache_size=4096

# Disable cache for deterministic performance (no cache overhead)
no_cache_fw = CIDARTHA(cache_size=0)

# Low-memory environment
low_memory_fw = CIDARTHA(cache_size=1024)
```

### Mixed Input Types (Production Scenario)

```python
import ipaddress
from CIDARTHA5 import CIDARTHA

firewall = CIDARTHA()
firewall.insert("192.168.0.0/16")

# All these use the SAME cache entry!
ip_str = "192.168.1.100"
ip_bytes = ipaddress.IPv4Address(ip_str).packed
ip_obj = ipaddress.IPv4Address(ip_str)

# First check creates cache entry
result1 = firewall.check(ip_str)      # Cache miss

# Subsequent checks with different types HIT the cache
result2 = firewall.check(ip_bytes)    # Cache HIT (same normalized key)
result3 = firewall.check(ip_obj)      # Cache HIT (same normalized key)

# All return the same result, but with cache efficiency!
assert result1 == result2 == result3
```

### Batch Operations

```python
# Batch insert for large datasets
cidr_list = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "203.0.113.0/24",
    "198.51.100.0/24"
]

firewall.batch_insert(cidr_list)
```

### Serialization and Persistence

```python
# Save firewall state to disk (cache_size is preserved!)
firewall = CIDARTHA(cache_size=8192)
firewall.insert("192.168.0.0/16")
firewall.insert("10.0.0.0/8")

# Serialize to bytes
serialized = firewall.dump()

# Save to file
with open("firewall_rules.msgpack", "wb") as f:
    f.write(serialized)

# Load from file
with open("firewall_rules.msgpack", "rb") as f:
    data = f.read()

# Restore firewall state (with original cache_size!)
restored_firewall = CIDARTHA.load(data)
print(restored_firewall._cache_size)  # 8192
restored_firewall.check("192.168.1.1")  # Returns True
```

### Thread-Safe Concurrent Operations

```python
import threading
from CIDARTHA5 import CIDARTHA

firewall = CIDARTHA()

def worker_insert(cidr_list):
    for cidr in cidr_list:
        firewall.insert(cidr)

def worker_check(ip_list):
    results = [firewall.check(ip) for ip in ip_list]
    return results

# Safe concurrent access
thread1 = threading.Thread(target=worker_insert, args=(["10.0.0.0/8"],))
thread2 = threading.Thread(target=worker_check, args=(["10.0.0.1"],))

thread1.start()
thread2.start()
thread1.join()
thread2.join()
```

### IPv6 Support

```python
firewall = CIDARTHA()

# IPv6 CIDR blocks
firewall.insert("2001:db8::/32")
firewall.insert("fe80::/10")
firewall.insert("::1/128")  # Loopback

# Check IPv6 addresses
firewall.check("2001:db8::1")      # Returns True
firewall.check("fe80::1")          # Returns True
firewall.check("2001:4860::8888")  # Returns False
```

## API Reference

### `CIDARTHA(cache_size: int = 4096)`

Creates a new CIDARTHA instance with configurable cache size.

**Parameters:**
- `cache_size` (int, optional): Maximum number of IP lookups to cache. Default is 4096.
  - Set to 0 to disable caching for deterministic performance
  - Increase for high-volume workloads (e.g., 8192, 16384)
  - Decrease for memory-constrained environments (e.g., 1024, 2048)

```python
# Default cache
firewall = CIDARTHA()

# Custom cache size
firewall = CIDARTHA(cache_size=8192)

# No cache
firewall = CIDARTHA(cache_size=0)
```

### `insert(input_data: str)`

Inserts a CIDR block into the trie. Thread-safe.

**Parameters:**
- `input_data` (str): CIDR notation string (e.g., "192.168.1.0/24")

**Raises:**
- `ValueError`: If the input is not a valid IP or CIDR range

```python
firewall.insert("192.168.1.0/24")
```

### `batch_insert(entries: list)`

Inserts multiple CIDR blocks efficiently with progress logging.

**Parameters:**
- `entries` (list): List of CIDR notation strings

```python
firewall.batch_insert(["10.0.0.0/8", "172.16.0.0/12"])
```

### `check(ip) -> bool`

Checks if an IP address matches any stored CIDR block. Optimized with normalized LRU caching.

**Parameters:**
- `ip`: IP address as string, bytes, int, or IPv4Address/IPv6Address object

**Returns:**
- `bool`: True if IP matches a stored CIDR block, False otherwise

**Note**: All input types are normalized to bytes before caching, ensuring efficient cache utilization.

```python
# All these use the same cache entry!
is_blocked = firewall.check("192.168.1.100")           # string
is_blocked = firewall.check(b"\xc0\xa8\x01\x64")      # bytes
is_blocked = firewall.check(ipaddress.IPv4Address("192.168.1.100"))  # object
```

### `remove(cidr: str)`

Removes a CIDR block from the trie. Thread-safe. Clears cache after removal.

**Parameters:**
- `cidr` (str): CIDR notation string to remove

**Raises:**
- `ValueError`: If the input is not a valid CIDR range

```python
firewall.remove("192.168.1.0/24")
```

### `clear()`

Removes all entries from the trie and clears the cache. Thread-safe.

```python
firewall.clear()
```

### `dump() -> bytes`

Serializes the entire trie to compact msgpack bytes. Cache size configuration is preserved.

**Returns:**
- `bytes`: Serialized trie data

```python
data = firewall.dump()
```

### `load(serialized_data: bytes) -> CIDARTHA`

Static method to deserialize a trie from msgpack bytes. Cache size is restored from serialized data.

**Parameters:**
- `serialized_data` (bytes): Serialized trie data

**Returns:**
- `CIDARTHA`: New CIDARTHA instance with restored data and cache configuration

```python
firewall = CIDARTHA.load(data)
```

## Performance Characteristics

### Time Complexity

- **Insert**: O(k) where k is the number of bits in the prefix (32 for IPv4, 128 for IPv6)
- **Lookup**: O(k) with normalized LRU cache for repeated queries
- **Remove**: O(k) with path pruning for memory efficiency
- **Batch Insert**: O(n*k) where n is the number of entries

### Space Complexity

- O(n*k) worst case, where n is the number of CIDR blocks
- Optimized with:
  - Lazy dictionary allocation (nodes without children use no dict space)
  - Compact tuple serialization
  - Minimal per-node overhead using `__slots__`
  - Efficient normalized caching (no duplicate entries for same IP)

### Optimizations

1. **C-Level Socket Conversions**: Direct use of `socket.inet_pton()` for fast IP parsing
2. **Normalized LRU Caching**: All input types converted to bytes before caching (NEW in v5)
3. **Configurable Cache Size**: Adjustable cache size for different workloads (NEW in v5)
4. **Pre-computed Bit Masks**: Eliminates runtime calculations
5. **Lazy Children Allocation**: Nodes only allocate child dictionaries when needed
6. **Direct Dictionary Access**: Bypasses method overhead in hot paths
7. **Fast Path for Bytes**: Skips normalization when input is already bytes

## Architecture

### CIDARTHANode

The trie node structure uses Python's `__slots__` for memory efficiency:

```python
@dataclass(slots=True)
class CIDARTHANode:
    is_end: bool                    # Marks CIDR block endpoint
    range_start: Optional[bytes]    # Network address
    range_end: Optional[bytes]      # Broadcast address
    _children: Optional[Dict]       # Lazy-allocated children
```

### Trie Structure

```
Root
├── [192] → Node
│   └── [168] → Node
│       └── [1] → Node (is_end=True, represents 192.168.1.0/24)
└── [10] → Node (is_end=True, represents 10.0.0.0/8)
```

Each byte of an IP address creates a path through the trie. CIDR blocks mark endpoint nodes with their network range.

### Cache Normalization (New in v5)

```
Input: "192.168.1.1" (string) → normalize to bytes → b"\xc0\xa8\x01\x01" → cache
Input: b"\xc0\xa8\x01\x01" (bytes) → already normalized → cache (HIT!)
Input: IPv4Address("192.168.1.1") → normalize to bytes → b"\xc0\xa8\x01\x01" → cache (HIT!)
```

All input types map to the same cache key, maximizing cache efficiency.

## Production Configuration Guide

### Choosing the Right Cache Size

| Workload Pattern | Recommended Cache Size | Rationale |
|------------------|------------------------|-----------|
| <1000 distinct IPs/burst | 1024-2048 | Small cache, low memory overhead |
| 1000-4000 distinct IPs/burst | 4096 (default) | Balanced performance |
| 4000-8000 distinct IPs/burst | 8192 | Prevent cache churn |
| >8000 distinct IPs/burst | 16384+ | High-volume systems |
| Deterministic performance needed | 0 (disabled) | No cache overhead |
| Mixed input types (string/bytes/objects) | 4096+ | Normalized caching shines here |

### Example Production Configurations

```python
# High-traffic web application firewall
web_firewall = CIDARTHA(cache_size=16384)

# Microservice API gateway (moderate traffic)
api_firewall = CIDARTHA(cache_size=4096)

# Embedded system (limited memory)
embedded_firewall = CIDARTHA(cache_size=512)

# Batch processing (no repeated lookups)
batch_processor = CIDARTHA(cache_size=0)
```

## Logging

CIDARTHA5 includes built-in logging for operations:

```python
import logging

# Configure CIDARTHA logger
logger = logging.getLogger("CIDARTHA")
logger.setLevel(logging.DEBUG)

# Now batch operations will log progress
firewall.batch_insert(large_cidr_list)
# Output:
# INFO:CIDARTHA:Starting batch insert of 1000 entries.
# INFO:CIDARTHA:Inserted 50/1000 (5.0%)
# INFO:CIDARTHA:Inserted 100/1000 (10.0%)
# ...
```

## Thread Safety

All mutating operations (`insert`, `remove`, `clear`, `batch_insert`) are protected by a reentrant lock (`RLock`). The `check` operation is read-only and relies on Python's GIL for atomicity.

```python
# Safe to use across multiple threads
firewall = CIDARTHA()

# Multiple threads can insert/check concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(firewall.insert, cidr_blocks)
```

## Testing

CIDARTHA5 includes comprehensive unit tests:

```bash
python3 test_cidartha5.py
```

Test coverage includes:
- Cache normalization (mixed input types)
- Configurable cache size
- Backwards compatibility with CIDARTHA4
- Performance improvements
- Edge cases and error handling

## Benchmarking

Run the included benchmark to compare CIDARTHA4 vs CIDARTHA5:

```bash
python3 benchmark.py
```

The benchmark tests:
1. Cache argument-sensitivity (fixed in v5)
2. Configurable cache size (new in v5)
3. Overall performance comparison
4. Mixed input types (real-world scenario)
5. Serialization with cache preservation

## Migration from CIDARTHA4

CIDARTHA5 is 100% backwards compatible with CIDARTHA4. Simply replace:

```python
# Old
from CIDARTHA4 import CIDARTHA

# New
from CIDARTHA5 import CIDARTHA
```

Optional: Take advantage of new features:

```python
# Tune cache size for your workload
firewall = CIDARTHA(cache_size=8192)

# Check cache performance
cache_info = firewall._check_cached.cache_info()
print(f"Hit rate: {cache_info.hits / (cache_info.hits + cache_info.misses):.2%}")
```

## Use Cases

- **Firewall Rules**: Fast IP filtering for network security applications
- **Rate Limiting**: Check if IPs belong to rate-limited ranges
- **GeoIP Filtering**: Block or allow traffic from specific network ranges
- **Security Scanning**: Identify IPs within suspicious ranges
- **Network Analysis**: Efficiently query IP membership across large datasets
- **Access Control**: Implement IP-based allowlists/blocklists
- **API Gateways**: High-performance IP-based routing and filtering
- **Web Application Firewalls**: Real-time IP threat detection

## Limitations

- **No Range Queries**: Doesn't support finding all IPs in a range (by design)
- **Exact CIDR Removal**: Remove requires exact CIDR match, not individual IPs
- **Memory Usage**: Large numbers of non-contiguous CIDR blocks can use significant memory
- **No Negation**: Cannot represent "all except this range" efficiently

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Changelog

### Version 5.0 (2026)
- ✨ Added normalized caching to fix argument-sensitivity issue
- ✨ Added configurable cache size via constructor parameter
- ✨ Cache configuration preserved in serialization
- ✨ Cache automatically cleared on remove/clear operations
- 🚀 14.4% faster on mixed input type workloads
- 🚀 21.9% faster when switching input types
- 📝 Added comprehensive unit tests
- 📝 Added production configuration guide

### Version 4.0
- Initial release with fixed cache size
- High-performance trie implementation
- Thread-safe operations
- msgpack serialization

## License

MIT License - Copyright (c) 2026 Jackson Cummings

See [LICENSE](LICENSE) file for details.

## Author

Jackson Cummings - [The Lab Corner](https://github.com/thelabcorner)

---

**CIDARTHA5** - Production-ready, fast, and efficient IP/CIDR management for Python 🚀
