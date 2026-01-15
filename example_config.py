#!/usr/bin/env python3
"""
Example demonstrating CIDARTHA configuration options.
"""

from CIDARTHA4 import CIDARTHA, configure_global_ip_cache
from config import CIDARTHAConfig, set_default_config
import logging

print("=" * 60)
print("CIDARTHA Configuration Examples")
print("=" * 60)

# Example 1: Default configuration
print("\n1. Using default configuration:")
fw = CIDARTHA()
fw.insert("192.168.1.0/24")
print(f"   Check cache size: {fw.check.cache_info().maxsize}")
print(f"   IP network cache size: {fw._cached_ip_network.cache_info().maxsize}")
print(f"   192.168.1.100 in firewall: {fw.check('192.168.1.100')}")

# Example 2: Custom cache sizes
print("\n2. Custom cache sizes (high-performance):")
config_hp = CIDARTHAConfig(
    ip_network_cache_size=8192,
    check_cache_size=8192
)
fw_hp = CIDARTHA(config=config_hp)
fw_hp.insert("10.0.0.0/8")
print(f"   Check cache size: {fw_hp.check.cache_info().maxsize}")
print(f"   IP network cache size: {fw_hp._cached_ip_network.cache_info().maxsize}")
print(f"   10.5.5.5 in firewall: {fw_hp.check('10.5.5.5')}")

# Example 3: Memory-constrained configuration
print("\n3. Memory-constrained configuration:")
config_low = CIDARTHAConfig(
    ip_network_cache_size=256,
    check_cache_size=256
)
fw_low = CIDARTHA(config=config_low)
fw_low.insert("172.16.0.0/12")
print(f"   Check cache size: {fw_low.check.cache_info().maxsize}")
print(f"   IP network cache size: {fw_low._cached_ip_network.cache_info().maxsize}")
print(f"   172.16.0.1 in firewall: {fw_low.check('172.16.0.1')}")

# Example 4: Custom logging
print("\n4. Custom logging configuration:")
config_log = CIDARTHAConfig(
    log_level=logging.DEBUG,
    batch_insert_log_interval=0.5  # Log every 50%
)
fw_log = CIDARTHA(config=config_log)
print(f"   Logger level: {logging.getLevelName(fw_log.config.log_level)}")
print(f"   Batch log interval: {fw_log.config.batch_insert_log_interval * 100}%")

# Example 5: Global IP cache configuration
print("\n5. Configuring global IP cache:")
print(f"   Default global IP cache size: 8192")
configure_global_ip_cache(16384)
print(f"   New global IP cache size: 16384")
fw_global = CIDARTHA()
fw_global.insert("203.0.113.0/24")
print(f"   203.0.113.1 in firewall: {fw_global.check('203.0.113.1')}")

# Example 6: Global default configuration
print("\n6. Setting global default configuration:")
set_default_config(CIDARTHAConfig(
    check_cache_size=2048,
    log_level=logging.WARNING
))
fw_default1 = CIDARTHA()
fw_default2 = CIDARTHA()
print(f"   Instance 1 check cache size: {fw_default1.check.cache_info().maxsize}")
print(f"   Instance 2 check cache size: {fw_default2.check.cache_info().maxsize}")

# Reset to defaults
set_default_config(CIDARTHAConfig())

print("\n" + "=" * 60)
print("Configuration examples completed successfully!")
print("=" * 60)
