# CIDARTHA

**C**IDR **I**P **D**iscrimination **A**nd **R**esolution **T**rie with **H**ybrid **A**lgorithms

A high-performance, thread-safe IP/CIDR firewall trie data structure for Python. CIDARTHA uses a memory-optimized binary trie to efficiently store and lookup IPv4/IPv6 CIDR blocks with blazing-fast performance.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

CIDARTHA4.py implements a specialized trie (prefix tree) data structure optimized for IP address and CIDR block operations. It's designed for applications that need fast IP filtering, firewall rules, IP allowlists/blocklists, or network range lookups.

### Key Features

- **⚡ High Performance**: O(k) insertion and lookup time complexity (k = IP address bits)
- **🔒 Thread-Safe**: Built with reentrant locks for concurrent operations
- **💾 Memory Optimized**: Binary trie structure with minimal dictionary overhead
- **📦 Serialization**: Compact msgpack-based persistence with efficient storage
- **🚀 LRU Caching**: Built-in caching for frequently checked IPs with configurable sizes
- **⚙️ Configurable**: Easily customize cache sizes, logging, and operational parameters
- **🔄 Full CRUD Operations**: Insert, remove, check, and clear with batch support
- **🌐 IPv4/IPv6 Support**: Handles both IPv4 and IPv6 addresses seamlessly
- **⚙️ C-Level Optimization**: Uses CPython's socket module for fast conversions

## Installation

### Requirements

```bash
pip install msgpack
```

### Basic Setup

Simply include `CIDARTHA4.py` in your project:

```python
from CIDARTHA4 import CIDARTHA
```

## Quick Start

```python
from CIDARTHA4 import CIDARTHA

# Create a new CIDARTHA instance
firewall = CIDARTHA()

# Insert CIDR blocks
firewall.insert("192.168.1.0/24")
firewall.insert("10.0.0.0/8")
firewall.insert("2001:db8::/32")  # IPv6 support

# Check if an IP is in the firewall
if firewall.check("192.168.1.100"):
    print("IP is blocked!")

if firewall.check("8.8.8.8"):
    print("IP is allowed")
else:
    print("IP not found in firewall rules")
```

## Usage Examples

### Basic Operations

```python
from CIDARTHA4 import CIDARTHA

# Initialize
firewall = CIDARTHA()

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
# Save firewall state to disk
firewall = CIDARTHA()
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

# Restore firewall state
restored_firewall = CIDARTHA.load(data)
restored_firewall.check("192.168.1.1")  # Returns True
```

### Thread-Safe Concurrent Operations

```python
import threading
from CIDARTHA4 import CIDARTHA

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

### Wildcard Matching

```python
firewall = CIDARTHA()

# Match all IPv4 addresses
firewall.insert("0.0.0.0/0")

# Now all IPv4 addresses match
firewall.check("1.2.3.4")      # Returns True
firewall.check("192.168.1.1")  # Returns True
```

## Configuration

CIDARTHA supports extensive configuration to customize cache sizes, logging behavior, and other operational parameters. Configuration is completely optional - CIDARTHA works with sensible defaults out of the box.

### Using Configuration

```python
from CIDARTHA4 import CIDARTHA, configure_global_ip_cache
from config import CIDARTHAConfig
import logging

# Create instance with custom configuration
config = CIDARTHAConfig(
    ip_network_cache_size=8192,      # Cache for ip_network objects
    check_cache_size=8192,            # Cache for IP lookup results
    log_level=logging.DEBUG,          # Logging level
    batch_insert_log_interval=0.1     # Log every 10% during batch insert
)
firewall = CIDARTHA(config=config)

# Or configure global IP cache (shared across all instances)
configure_global_ip_cache(16384)  # Increase global IP cache to 16384
```

### Configuration Options

The `CIDARTHAConfig` dataclass provides the following options:

- **`ip_to_bytes_cache_size`** (int, default: 8192): LRU cache size for IP string to bytes conversion. This cache is global and shared across all CIDARTHA instances. Use `configure_global_ip_cache()` to adjust it at runtime.

- **`ip_network_cache_size`** (int, default: 4096): LRU cache size for `ip_network` objects used during insertion.

- **`check_cache_size`** (int, default: 4096): LRU cache size for IP lookup results. Frequently checked IPs will be served from cache.

- **`log_level`** (int, default: `logging.INFO`): Logging level for the CIDARTHA logger. Options: `logging.DEBUG`, `logging.INFO`, `logging.WARNING`, `logging.ERROR`.

- **`batch_insert_log_interval`** (float, default: 0.05): Progress logging interval for batch inserts as a fraction (0.05 = 5%, meaning log every 5% of entries).

### Configuration Examples

#### Memory-Constrained Environments

```python
# Reduce cache sizes for low-memory systems
config = CIDARTHAConfig(
    ip_network_cache_size=512,
    check_cache_size=512
)
firewall = CIDARTHA(config=config)
```

#### High-Performance Environments

```python
# Increase cache sizes for better performance
config = CIDARTHAConfig(
    ip_network_cache_size=16384,
    check_cache_size=16384
)
configure_global_ip_cache(32768)
firewall = CIDARTHA(config=config)
```

#### Custom Logging

```python
# Enable debug logging and more frequent progress updates
config = CIDARTHAConfig(
    log_level=logging.DEBUG,
    batch_insert_log_interval=0.1  # Log every 10%
)
firewall = CIDARTHA(config=config)
```

#### Global Default Configuration

```python
# Set a global default configuration for all new instances
from config import set_default_config, CIDARTHAConfig

set_default_config(CIDARTHAConfig(
    check_cache_size=8192,
    log_level=logging.WARNING
))

# All new instances will use this configuration
fw1 = CIDARTHA()  # Uses global default
fw2 = CIDARTHA()  # Also uses global default
```

## API Reference

### `CIDARTHA(config=None)`

Creates a new CIDARTHA instance.

**Parameters:**
- `config` (CIDARTHAConfig, optional): Configuration object. If None, uses global default configuration.

```python
# Default configuration
firewall = CIDARTHA()

# Custom configuration
from config import CIDARTHAConfig
config = CIDARTHAConfig(check_cache_size=8192)
firewall = CIDARTHA(config=config)
```

### `configure_global_ip_cache(cache_size: int = 8192)`

Configure the global IP to bytes cache size (module-level function).

**Parameters:**
- `cache_size` (int): Maximum number of IP addresses to cache

```python
from CIDARTHA4 import configure_global_ip_cache
configure_global_ip_cache(16384)  # Double the default cache size
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

Checks if an IP address matches any stored CIDR block. Optimized with LRU caching.

**Parameters:**
- `ip`: IP address as string, bytes, int, or IPv4Address/IPv6Address object

**Returns:**
- `bool`: True if IP matches a stored CIDR block, False otherwise

```python
is_blocked = firewall.check("192.168.1.100")
```

### `remove(cidr: str)`

Removes a CIDR block from the trie. Thread-safe.

**Parameters:**
- `cidr` (str): CIDR notation string to remove

**Raises:**
- `ValueError`: If the input is not a valid CIDR range

```python
firewall.remove("192.168.1.0/24")
```

### `clear()`

Removes all entries from the trie. Thread-safe.

```python
firewall.clear()
```

### `dump() -> bytes`

Serializes the entire trie to compact msgpack bytes.

**Returns:**
- `bytes`: Serialized trie data

```python
data = firewall.dump()
```

### `load(serialized_data: bytes, config=None) -> CIDARTHA`

Static method to deserialize a trie from msgpack bytes.

**Parameters:**
- `serialized_data` (bytes): Serialized trie data
- `config` (CIDARTHAConfig, optional): Configuration for the loaded instance

**Returns:**
- `CIDARTHA`: New CIDARTHA instance with restored data

```python
# Load with default configuration
firewall = CIDARTHA.load(data)

# Load with custom configuration
config = CIDARTHAConfig(check_cache_size=8192)
firewall = CIDARTHA.load(data, config=config)
```

## Performance Characteristics

### Time Complexity

- **Insert**: O(k) where k is the number of bits in the prefix (32 for IPv4, 128 for IPv6)
- **Lookup**: O(k) with LRU cache for repeated queries
- **Remove**: O(k) with path pruning for memory efficiency
- **Batch Insert**: O(n*k) where n is the number of entries

### Space Complexity

- O(n*k) worst case, where n is the number of CIDR blocks
- Optimized with:
  - Lazy dictionary allocation (nodes without children use no dict space)
  - Compact tuple serialization
  - Minimal per-node overhead using `__slots__`

### Optimizations

1. **C-Level Socket Conversions**: Direct use of `socket.inet_pton()` for fast IP parsing
2. **Dual-Layer LRU Caching**: 
   - 4096-entry cache for frequently checked IPs (check results)
   - 8192-entry cache for IP string to bytes conversion
3. **Pre-computed Bit Masks**: Eliminates runtime calculations
4. **Lazy Children Allocation**: Nodes only allocate child dictionaries when needed
5. **Direct Dictionary Access**: Bypasses method overhead in hot paths
6. **Batch Operation Optimization**: Cache cleared once per batch instead of per operation
7. **Local Variable Caching**: Hot-path attribute lookups reduced via local references

## Benchmarks

Real-world performance benchmarks using [Firehol blocklist-ipsets](https://github.com/firehol/blocklist-ipsets) data (277,166 CIDR blocks from firehol_level1, firehol_level2, firehol_level3, firehol_level4, firehol_webserver, and firehol_abusers_30d):

### Insertion Performance
- **Insertion Rate**: 68.85 K entries/second
- **Average Time per Insert**: 14.52 μs
- **Memory Usage**: 98.38 MB (0.36 KB per entry)

### Lookup Performance
- **Lookup Rate**: 675.89 K lookups/second (cold cache)
- **Lookup Rate**: 9.56 M lookups/second (warm cache)
- **Average Time per Lookup**: 1.48 μs (cold), 0.10 μs (warm)
- **Cache Hit Rate**: Up to 100% (with dual-layer LRU caching)

### Serialization Performance
- **Serialized Size**: 6.04 MB (16.3 MB → 6.04 MB, 2.7:1 compression)
- **Serialization Time**: 960.01 ms
- **Deserialization Time**: 1.27 s

### Benchmark Notes

- Benchmarks performed on standard GitHub Actions runner hardware
- Dataset: 277,166 unique CIDR blocks from Firehol blocklist-ipsets
- Lookup benchmark: 100,000 IP address checks
- Memory measurements exclude Python interpreter overhead
- Warm cache performance can exceed 9.5M lookups/sec with repeated queries

**Credits**: Benchmark data provided by [Firehol blocklist-ipsets](https://github.com/firehol/blocklist-ipsets), a collection of IP blacklists for network security.

To run the benchmark yourself:

```bash
python3 benchmark.py
```

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

## Logging

CIDARTHA includes built-in logging for operations:

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

## Use Cases

- **Firewall Rules**: Fast IP filtering for network security applications
- **Rate Limiting**: Check if IPs belong to rate-limited ranges
- **GeoIP Filtering**: Block or allow traffic from specific network ranges
- **Security Scanning**: Identify IPs within suspicious ranges
- **Network Analysis**: Efficiently query IP membership across large datasets
- **Access Control**: Implement IP-based allowlists/blocklists

## Limitations

- **No Range Queries**: Doesn't support finding all IPs in a range (by design)
- **Exact CIDR Removal**: Remove requires exact CIDR match, not individual IPs
- **Memory Usage**: Large numbers of non-contiguous CIDR blocks can use significant memory
- **No Negation**: Cannot represent "all except this range" efficiently

## License

MIT License - Copyright (c) 2026 Jackson Cummings

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Author

Jackson Cummings - [The Lab Corner](https://github.com/thelabcorner)

---

**CIDARTHA** - Fast, efficient, and thread-safe IP/CIDR management for Python 🚀
