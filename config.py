"""
Configuration module for CIDARTHA.

This module provides configurable settings for CIDARTHA, allowing users to 
easily customize cache sizes, logging behavior, and other operational parameters.
"""

import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class CIDARTHAConfig:
    """
    Configuration class for CIDARTHA.
    
    Attributes:
        ip_to_bytes_cache_size: LRU cache size for IP string to bytes conversion (default: 8192)
                                Note: This cache is global and shared across all instances.
                                Use configure_global_ip_cache() to adjust it at runtime.
        ip_network_cache_size: LRU cache size for ip_network objects (default: 4096)
        check_cache_size: LRU cache size for IP lookup results (default: 4096)
        log_level: Logging level for CIDARTHA logger (default: logging.INFO)
        batch_insert_log_interval: Progress logging interval for batch inserts as a fraction 
                                   (default: 0.05 = 5%, i.e., log every 5% of total entries)
    
    Examples:
        >>> # Use default configuration
        >>> config = CIDARTHAConfig()
        >>> fw = CIDARTHA(config=config)
        
        >>> # Customize cache sizes for memory-constrained environments
        >>> config = CIDARTHAConfig(
        ...     ip_network_cache_size=512,
        ...     check_cache_size=512
        ... )
        >>> fw = CIDARTHA(config=config)
        
        >>> # Increase cache sizes for high-performance requirements
        >>> config = CIDARTHAConfig(
        ...     ip_network_cache_size=8192,
        ...     check_cache_size=8192
        ... )
        >>> fw = CIDARTHA(config=config)
        
        >>> # Customize logging
        >>> config = CIDARTHAConfig(
        ...     log_level=logging.DEBUG,
        ...     batch_insert_log_interval=0.1  # Log every 10%
        ... )
        >>> fw = CIDARTHA(config=config)
    """
    ip_to_bytes_cache_size: int = 8192
    ip_network_cache_size: int = 4096
    check_cache_size: int = 4096
    log_level: int = logging.INFO
    batch_insert_log_interval: float = 0.05  # 5% = 1/20
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.ip_to_bytes_cache_size < 0:
            raise ValueError("ip_to_bytes_cache_size must be non-negative")
        if self.ip_network_cache_size < 0:
            raise ValueError("ip_network_cache_size must be non-negative")
        if self.check_cache_size < 0:
            raise ValueError("check_cache_size must be non-negative")
        if not (0 < self.batch_insert_log_interval <= 1.0):
            raise ValueError("batch_insert_log_interval must be between 0 and 1.0")


# Global default configuration instance
_default_config: Optional[CIDARTHAConfig] = None


def get_default_config() -> CIDARTHAConfig:
    """
    Get the global default configuration.
    
    Returns:
        CIDARTHAConfig: The global default configuration instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = CIDARTHAConfig()
    return _default_config


def set_default_config(config: CIDARTHAConfig) -> None:
    """
    Set the global default configuration.
    
    This allows users to set a default configuration that will be used by all
    new CIDARTHA instances unless they explicitly provide their own config.
    
    Args:
        config: The configuration to use as the global default.
    
    Example:
        >>> from CIDARTHA4 import CIDARTHA
        >>> from config import CIDARTHAConfig, set_default_config
        >>> 
        >>> # Set global default with larger caches
        >>> set_default_config(CIDARTHAConfig(check_cache_size=8192))
        >>> 
        >>> # All new instances will use this config
        >>> fw1 = CIDARTHA()
        >>> fw2 = CIDARTHA()
    """
    global _default_config
    _default_config = config
