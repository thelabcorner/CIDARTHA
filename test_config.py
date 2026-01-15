#!/usr/bin/env python3
"""
Tests for CIDARTHA configuration functionality.
"""
import unittest
import logging
from CIDARTHA4 import CIDARTHA, configure_global_ip_cache
from config import CIDARTHAConfig, get_default_config, set_default_config


class TestCIDARTHAConfiguration(unittest.TestCase):
    """Test configuration functionality."""
    
    def test_default_config(self):
        """Test CIDARTHA with default configuration."""
        fw = CIDARTHA()
        self.assertIsNotNone(fw.config)
        self.assertEqual(fw.config.ip_network_cache_size, 4096)
        self.assertEqual(fw.config.check_cache_size, 4096)
        self.assertEqual(fw.config.log_level, logging.INFO)
        self.assertEqual(fw.config.batch_insert_log_interval, 0.05)
    
    def test_custom_config(self):
        """Test CIDARTHA with custom configuration."""
        config = CIDARTHAConfig(
            ip_network_cache_size=1024,
            check_cache_size=512,
            log_level=logging.DEBUG,
            batch_insert_log_interval=0.1
        )
        fw = CIDARTHA(config=config)
        self.assertEqual(fw.config.ip_network_cache_size, 1024)
        self.assertEqual(fw.config.check_cache_size, 512)
        self.assertEqual(fw.config.log_level, logging.DEBUG)
        self.assertEqual(fw.config.batch_insert_log_interval, 0.1)
    
    def test_config_functionality(self):
        """Test that configuration actually affects behavior."""
        # Create instance with smaller cache
        config = CIDARTHAConfig(check_cache_size=2)
        fw = CIDARTHA(config=config)
        
        # Insert and check
        fw.insert("192.168.1.0/24")
        self.assertTrue(fw.check("192.168.1.1"))
        
        # Verify cache info (cache should work)
        cache_info = fw.check.cache_info()
        self.assertEqual(cache_info.maxsize, 2)
    
    def test_global_default_config(self):
        """Test global default configuration."""
        # Set a global default
        custom_config = CIDARTHAConfig(check_cache_size=8192)
        set_default_config(custom_config)
        
        # Create new instance without explicit config
        fw = CIDARTHA()
        self.assertEqual(fw.config.check_cache_size, 8192)
        
        # Reset to default
        set_default_config(CIDARTHAConfig())
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Invalid cache size
        with self.assertRaises(ValueError):
            CIDARTHAConfig(check_cache_size=-1)
        
        # Invalid log interval (too small)
        with self.assertRaises(ValueError):
            CIDARTHAConfig(batch_insert_log_interval=0)
        
        # Invalid log interval (too large)
        with self.assertRaises(ValueError):
            CIDARTHAConfig(batch_insert_log_interval=1.5)
    
    def test_serialization_with_config(self):
        """Test that serialization works with config."""
        config = CIDARTHAConfig(check_cache_size=1024)
        fw1 = CIDARTHA(config=config)
        fw1.insert("10.0.0.0/8")
        
        # Serialize
        data = fw1.dump()
        
        # Deserialize with same config
        fw2 = CIDARTHA.load(data, config=config)
        self.assertTrue(fw2.check("10.0.0.1"))
        self.assertEqual(fw2.config.check_cache_size, 1024)
    
    def test_configure_global_ip_cache(self):
        """Test global IP cache configuration."""
        # This should not raise an error
        configure_global_ip_cache(4096)
        
        # Verify it still works
        fw = CIDARTHA()
        fw.insert("192.168.1.0/24")
        self.assertTrue(fw.check("192.168.1.1"))
    
    def test_backward_compatibility(self):
        """Test that old code without config still works."""
        # This simulates old code that doesn't know about config
        fw = CIDARTHA(config=None)
        fw.insert("192.168.1.0/24")
        self.assertTrue(fw.check("192.168.1.1"))
        self.assertFalse(fw.check("10.0.0.1"))
    
    def test_batch_insert_with_custom_log_interval(self):
        """Test batch insert with custom log interval."""
        config = CIDARTHAConfig(batch_insert_log_interval=0.5)  # Log every 50%
        fw = CIDARTHA(config=config)
        
        cidrs = [f"10.{i}.0.0/16" for i in range(10)]
        fw.batch_insert(cidrs)
        
        # Verify insertions worked
        self.assertTrue(fw.check("10.0.1.1"))
        self.assertTrue(fw.check("10.5.1.1"))
        self.assertTrue(fw.check("10.9.1.1"))


class TestCIDARTHAConfigModule(unittest.TestCase):
    """Test the config module itself."""
    
    def test_config_dataclass(self):
        """Test config dataclass creation."""
        config = CIDARTHAConfig()
        self.assertEqual(config.ip_to_bytes_cache_size, 8192)
        self.assertEqual(config.ip_network_cache_size, 4096)
        self.assertEqual(config.check_cache_size, 4096)
        self.assertEqual(config.log_level, logging.INFO)
        self.assertEqual(config.batch_insert_log_interval, 0.05)
    
    def test_config_with_custom_values(self):
        """Test config with custom values."""
        config = CIDARTHAConfig(
            ip_to_bytes_cache_size=16384,
            ip_network_cache_size=8192,
            check_cache_size=8192,
            log_level=logging.WARNING,
            batch_insert_log_interval=0.25
        )
        self.assertEqual(config.ip_to_bytes_cache_size, 16384)
        self.assertEqual(config.ip_network_cache_size, 8192)
        self.assertEqual(config.check_cache_size, 8192)
        self.assertEqual(config.log_level, logging.WARNING)
        self.assertEqual(config.batch_insert_log_interval, 0.25)
    
    def test_get_default_config(self):
        """Test get_default_config function."""
        config = get_default_config()
        self.assertIsNotNone(config)
        self.assertIsInstance(config, CIDARTHAConfig)
    
    def test_set_and_get_default_config(self):
        """Test setting and getting default config."""
        # Create custom config
        custom = CIDARTHAConfig(check_cache_size=2048)
        set_default_config(custom)
        
        # Get it back
        retrieved = get_default_config()
        self.assertEqual(retrieved.check_cache_size, 2048)
        
        # Reset
        set_default_config(CIDARTHAConfig())


def run_tests():
    """Run all configuration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHAConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHAConfigModule))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
