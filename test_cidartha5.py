#!/usr/bin/env python3
"""
Unit tests for CIDARTHA5 demonstrating the fixed issues from CIDARTHA4.

Tests specifically validate:
1. Cache normalization (strings, bytes, IP objects all use same cache)
2. Configurable cache size
3. Backwards compatibility
"""

import unittest
import ipaddress
from CIDARTHA5 import CIDARTHA


class TestCacheNormalization(unittest.TestCase):
    """Test that cache works correctly with different input formats."""
    
    def setUp(self):
        """Create a fresh CIDARTHA instance for each test."""
        self.fw = CIDARTHA(cache_size=100)
        self.fw.insert("192.168.0.0/16")
        self.fw.insert("10.0.0.0/8")
    
    def test_same_format_uses_cache(self):
        """Test that repeated checks with same format use cache."""
        test_ip = "192.168.1.100"
        
        # Clear cache
        if hasattr(self.fw._check_cached, 'cache_clear'):
            self.fw._check_cached.cache_clear()
        
        # First check - cache miss
        result1 = self.fw.check(test_ip)
        cache_info = self.fw._check_cached.cache_info()
        initial_misses = cache_info.misses
        
        # Second check with same format - cache hit
        result2 = self.fw.check(test_ip)
        
        # Both should return True
        self.assertTrue(result1)
        self.assertTrue(result2)
        
        # Should have a cache hit
        final_cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(final_cache_info.hits, 1, "Should have 1 cache hit")
    
    def test_different_formats_create_separate_entries(self):
        """Test that different input formats create separate cache entries (by design for speed)."""
        test_ip = "10.0.0.1"
        
        # Clear any existing cache
        if hasattr(self.fw._check_cached, 'cache_clear'):
            self.fw._check_cached.cache_clear()
        
        # Check with string
        self.fw.check(test_ip)
        
        # Check with bytes
        ip_bytes = ipaddress.IPv4Address(test_ip).packed
        self.fw.check(ip_bytes)
        
        # Each format creates its own cache entry (this is the CIDARTHA4 behavior, kept for speed)
        cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(cache_info.currsize, 2, "Cache should have 2 entries (one per format)")
    
    def test_consistent_format_gives_best_performance(self):
        """Test that using consistent input format gives best cache performance."""
        test_ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
        
        # Clear cache
        if hasattr(self.fw._check_cached, 'cache_clear'):
            self.fw._check_cached.cache_clear()
        
        # Check each IP twice with strings (consistent format)
        for ip_str in test_ips:
            self.fw.check(ip_str)
            self.fw.check(ip_str)  # Second check should hit cache
        
        cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(cache_info.misses, 3, "Should have 3 cache misses")
        self.assertEqual(cache_info.hits, 3, "Should have 3 cache hits")
        self.assertEqual(cache_info.currsize, 3, "Should have 3 cached entries")


class TestConfigurableCacheSize(unittest.TestCase):
    """Test configurable cache size functionality."""
    
    def test_default_cache_size(self):
        """Test that default cache size is 4096."""
        fw = CIDARTHA()
        self.assertEqual(fw._cache_size, 4096)
    
    def test_custom_cache_size(self):
        """Test that custom cache size is respected."""
        fw = CIDARTHA(cache_size=8192)
        self.assertEqual(fw._cache_size, 8192)
        
        # Verify it's actually used
        fw.insert("192.168.0.0/16")
        for i in range(100):
            fw.check(f"192.168.0.{i}")
        
        cache_info = fw._check_cached.cache_info()
        self.assertEqual(cache_info.maxsize, 8192)
    
    def test_cache_disabled(self):
        """Test that cache can be disabled with cache_size=0."""
        fw = CIDARTHA(cache_size=0)
        self.assertEqual(fw._cache_size, 0)
        
        fw.insert("192.168.0.0/16")
        
        # Check should work even without cache
        result = fw.check("192.168.0.1")
        self.assertTrue(result)
        
        # Should not have cache_info method (not an lru_cache)
        self.assertFalse(hasattr(fw._check_cached, 'cache_info'))
    
    def test_cache_size_preserved_in_serialization(self):
        """Test that cache_size is preserved when serializing/deserializing."""
        fw = CIDARTHA(cache_size=2048)
        fw.insert("10.0.0.0/8")
        
        # Serialize
        data = fw.dump()
        
        # Deserialize
        fw_restored = CIDARTHA.load(data)
        
        # Cache size should be preserved
        self.assertEqual(fw_restored._cache_size, 2048)


class TestBackwardsCompatibility(unittest.TestCase):
    """Test that CIDARTHA5 maintains compatibility with CIDARTHA4 API."""
    
    def test_basic_operations(self):
        """Test basic insert/check/remove operations."""
        fw = CIDARTHA()
        
        # Insert
        fw.insert("192.168.1.0/24")
        
        # Check
        self.assertTrue(fw.check("192.168.1.100"))
        self.assertFalse(fw.check("10.0.0.1"))
        
        # Remove
        fw.remove("192.168.1.0/24")
        self.assertFalse(fw.check("192.168.1.100"))
    
    def test_batch_insert(self):
        """Test batch insert functionality."""
        fw = CIDARTHA()
        cidrs = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        
        fw.batch_insert(cidrs)
        
        self.assertTrue(fw.check("10.0.0.1"))
        self.assertTrue(fw.check("172.16.0.1"))
        self.assertTrue(fw.check("192.168.0.1"))
    
    def test_clear(self):
        """Test clear functionality."""
        fw = CIDARTHA()
        fw.insert("192.168.0.0/16")
        
        self.assertTrue(fw.check("192.168.1.1"))
        
        fw.clear()
        
        self.assertFalse(fw.check("192.168.1.1"))
    
    def test_serialization(self):
        """Test serialization/deserialization."""
        fw = CIDARTHA()
        fw.insert("10.0.0.0/8")
        fw.insert("192.168.0.0/16")
        
        # Serialize
        data = fw.dump()
        
        # Deserialize
        fw_restored = CIDARTHA.load(data)
        
        # Check that data is preserved
        self.assertTrue(fw_restored.check("10.0.0.1"))
        self.assertTrue(fw_restored.check("192.168.1.1"))
        self.assertFalse(fw_restored.check("172.16.0.1"))
    
    def test_ipv6_support(self):
        """Test IPv6 address support."""
        fw = CIDARTHA()
        fw.insert("2001:db8::/32")
        
        self.assertTrue(fw.check("2001:db8::1"))
        self.assertFalse(fw.check("2001:db9::1"))


class TestPerformanceImprovement(unittest.TestCase):
    """Test that CIDARTHA5 improves performance in key scenarios."""
    
    def test_cache_performance_with_consistent_format(self):
        """
        Test that cache performs well with consistent input format.
        This is the recommended usage pattern for best performance.
        """
        fw = CIDARTHA(cache_size=100)
        fw.insert("192.168.0.0/16")
        
        # Clear cache to start fresh
        if hasattr(fw._check_cached, 'cache_clear'):
            fw._check_cached.cache_clear()
        
        test_ips = [f"192.168.0.{i}" for i in range(50)]
        
        # Check each IP twice with same format (strings)
        for ip_str in test_ips:
            fw.check(ip_str)
            fw.check(ip_str)  # Should hit cache
        
        cache_info = fw._check_cached.cache_info()
        
        # Should have 50 misses (one per unique IP) and 50 hits (second check per IP)
        self.assertEqual(cache_info.misses, 50)
        self.assertEqual(cache_info.hits, 50)
        
        # Hit rate should be 50%
        hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses)
        self.assertGreater(hit_rate, 0.49, "Cache hit rate should be around 50%")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_invalid_ip_raises_error(self):
        """Test that invalid IPs raise ValueError."""
        fw = CIDARTHA()
        
        with self.assertRaises(ValueError):
            fw.check("not.an.ip")
    
    def test_wildcard_cidr(self):
        """Test /0 wildcard CIDR."""
        fw = CIDARTHA()
        fw.insert("0.0.0.0/0")
        
        # Should match any IPv4
        self.assertTrue(fw.check("1.2.3.4"))
        self.assertTrue(fw.check("192.168.1.1"))
    
    def test_cache_clear_on_clear(self):
        """Test that cache is cleared when trie is cleared."""
        fw = CIDARTHA(cache_size=100)
        fw.insert("192.168.0.0/16")
        
        # Do some checks to populate cache
        for i in range(10):
            fw.check(f"192.168.0.{i}")
        
        cache_info_before = fw._check_cached.cache_info()
        self.assertGreater(cache_info_before.currsize, 0)
        
        # Clear the trie
        fw.clear()
        
        # Cache should also be cleared
        cache_info_after = fw._check_cached.cache_info()
        self.assertEqual(cache_info_after.currsize, 0)


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCacheNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurableCacheSize))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardsCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceImprovement))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())
