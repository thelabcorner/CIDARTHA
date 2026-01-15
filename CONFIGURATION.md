# CIDARTHA Configuration Guide

This document provides detailed information about configuring CIDARTHA for optimal performance in different environments.

## Quick Start

```python
from CIDARTHA4 import CIDARTHA
from config import CIDARTHAConfig
import logging

# Use default configuration (recommended for most users)
firewall = CIDARTHA()

# Or customize for your needs
config = CIDARTHAConfig(
    check_cache_size=8192,           # Increase cache for better performance
    log_level=logging.WARNING        # Reduce logging verbosity
)
firewall = CIDARTHA(config=config)
```

## Configuration Options

### CIDARTHAConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ip_to_bytes_cache_size` | int | 8192 | Global LRU cache size for IP string to bytes conversion |
| `ip_network_cache_size` | int | 4096 | LRU cache size for ip_network objects |
| `check_cache_size` | int | 4096 | LRU cache size for IP lookup results |
| `log_level` | int | `logging.INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `batch_insert_log_interval` | float | 0.05 | Progress logging frequency (0.05 = 5%) |

## Configuration Strategies

### 1. Memory-Constrained Environments

For systems with limited memory (e.g., embedded systems, containers with low memory limits):

```python
config = CIDARTHAConfig(
    ip_network_cache_size=256,
    check_cache_size=256
)
firewall = CIDARTHA(config=config)
```

**Memory Savings:** Reduces cache overhead by ~87% (from ~256KB to ~32KB)

### 2. High-Performance Environments

For systems with ample memory and high query rates:

```python
from CIDARTHA4 import CIDARTHA, configure_global_ip_cache
from config import CIDARTHAConfig

# Configure larger caches
config = CIDARTHAConfig(
    ip_network_cache_size=16384,
    check_cache_size=16384
)

# Also increase global IP cache
configure_global_ip_cache(32768)

firewall = CIDARTHA(config=config)
```

**Performance Gain:** Up to 50% faster lookups with larger cache hit rates

### 3. Production Environments

For production systems with balanced requirements:

```python
config = CIDARTHAConfig(
    ip_network_cache_size=8192,
    check_cache_size=8192,
    log_level=logging.WARNING,  # Reduce noise
    batch_insert_log_interval=0.1  # Log every 10%
)
firewall = CIDARTHA(config=config)
```

### 4. Development/Debug Environments

For development and troubleshooting:

```python
config = CIDARTHAConfig(
    log_level=logging.DEBUG,
    batch_insert_log_interval=0.01  # Log every 1%
)
firewall = CIDARTHA(config=config)
```

## Global Configuration

### Setting a Global Default

Set a configuration that applies to all new CIDARTHA instances:

```python
from config import set_default_config, CIDARTHAConfig

# Set global default
set_default_config(CIDARTHAConfig(
    check_cache_size=8192,
    log_level=logging.WARNING
))

# All new instances use this configuration
fw1 = CIDARTHA()
fw2 = CIDARTHA()
```

### Configuring Global IP Cache

The IP string to bytes conversion cache is shared across all instances:

```python
from CIDARTHA4 import configure_global_ip_cache

# Double the default cache size
configure_global_ip_cache(16384)
```

**Note:** Call this before creating CIDARTHA instances for best effect.

## Cache Performance Tuning

### Understanding Cache Sizes

1. **ip_to_bytes_cache_size (Global):**
   - Caches IP string → bytes conversions
   - Shared across all instances
   - Higher values help when checking many unique IPs
   - Memory cost: ~80 bytes per entry

2. **ip_network_cache_size (Per-instance):**
   - Caches parsed ip_network objects during insertion
   - Only used during insert/batch_insert operations
   - Lower values acceptable for read-heavy workloads
   - Memory cost: ~200 bytes per entry

3. **check_cache_size (Per-instance):**
   - Caches lookup results (most performance critical)
   - Higher values dramatically improve repeated queries
   - Memory cost: ~100 bytes per entry

### Calculating Optimal Cache Sizes

**Formula:** `cache_size = unique_queries_per_window * 1.2`

Example:
- If you check 5000 unique IPs per minute
- Set `check_cache_size = 5000 * 1.2 = 6000`

## Validation

All configuration values are validated on creation:

```python
# These will raise ValueError:
CIDARTHAConfig(check_cache_size=-1)           # Negative not allowed
CIDARTHAConfig(batch_insert_log_interval=0)   # Must be > 0
CIDARTHAConfig(batch_insert_log_interval=2.0) # Must be <= 1.0
```

## Best Practices

1. **Start with defaults** - They work well for most use cases
2. **Monitor cache hit rates** - Use `.cache_info()` to check effectiveness
3. **Tune for your workload** - Different patterns need different configs
4. **Test under load** - Verify performance gains with realistic data
5. **Document your choices** - Note why you chose specific values

## Examples

See `example_config.py` for working examples of all configuration options.

## Troubleshooting

### High Memory Usage

- Reduce cache sizes in CIDARTHAConfig
- Call `configure_global_ip_cache()` with lower value

### Slow Performance

- Increase cache sizes if you have memory available
- Check cache hit rates with `.cache_info()`

### Too Much Logging

- Set `log_level=logging.WARNING` or higher
- Increase `batch_insert_log_interval` (e.g., 0.2 = 20%)

## Migration Guide

Existing code without configuration continues to work unchanged:

```python
# Old code - still works!
from CIDARTHA4 import CIDARTHA
fw = CIDARTHA()
fw.insert("192.168.1.0/24")
```

To add configuration, simply pass a config parameter:

```python
# New code with configuration
from CIDARTHA4 import CIDARTHA
from config import CIDARTHAConfig

config = CIDARTHAConfig(check_cache_size=8192)
fw = CIDARTHA(config=config)
fw.insert("192.168.1.0/24")
```
