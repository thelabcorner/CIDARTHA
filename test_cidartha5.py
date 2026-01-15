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
    """Test that cache normalization works correctly."""
    
    def setUp(self):
        """Create a fresh CIDARTHA instance for each test."""
        self.fw = CIDARTHA(cache_size=100)
        self.fw.insert("192.168.0.0/16")
        self.fw.insert("10.0.0.0/8")
    
    def test_same_ip_different_formats_share_cache(self):
        """Test that string, bytes, and IP object formats share cache entries."""
        test_ip = "192.168.1.100"
        
        # First check with string - should create cache entry
        result1 = self.fw.check(test_ip)
        initial_misses = self.fw._check_cached.cache_info().misses
        
        # Check with bytes - should HIT the cache (normalized to same bytes)
        ip_bytes = ipaddress.IPv4Address(test_ip).packed
        result2 = self.fw.check(ip_bytes)
        
        # Check with IP object - should also HIT the cache
        ip_obj = ipaddress.IPv4Address(test_ip)
        result3 = self.fw.check(ip_obj)
        
        # All should return True
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)
        
        # Should only have 1 cache miss (the initial check)
        final_cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(final_cache_info.misses, initial_misses)
        self.assertEqual(final_cache_info.hits, 2, "Should have 2 cache hits (bytes and IP object)")
    
    def test_cache_key_is_normalized(self):
        """Test that cache uses normalized bytes as key."""
        test_ip = "10.0.0.1"
        
        # Clear any existing cache
        self.fw._check_cached.cache_clear()
        
        # Check with string
        self.fw.check(test_ip)
        
        # Check with bytes
        ip_bytes = ipaddress.IPv4Address(test_ip).packed
        self.fw.check(ip_bytes)
        
        # Should only have 1 cache entry (both normalized to same key)
        cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(cache_info.currsize, 1, "Cache should have only 1 entry")
    
    def test_mixed_format_lookups(self):
        """Test realistic scenario with mixed input formats."""
        test_ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
        
        # Clear cache
        self.fw._check_cached.cache_clear()
        
        # Check each IP in three different formats
        for ip_str in test_ips:
            self.fw.check(ip_str)
            self.fw.check(ipaddress.IPv4Address(ip_str).packed)
            self.fw.check(ipaddress.IPv4Address(ip_str))
        
        # Should have 3 misses (one per unique IP) and 6 hits (2 additional formats per IP)
        cache_info = self.fw._check_cached.cache_info()
        self.assertEqual(cache_info.misses, 3, "Should have 3 cache misses")
        self.assertEqual(cache_info.hits, 6, "Should have 6 cache hits")
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
    
    def test_cache_hit_rate_with_mixed_types(self):
        """
        Test that cache hit rate is significantly better with mixed input types.
        This is the key improvement in CIDARTHA5.
        """
        fw = CIDARTHA(cache_size=100)
        fw.insert("192.168.0.0/16")
        
        # Clear cache to start fresh
        fw._check_cached.cache_clear()
        
        test_ips = [f"192.168.0.{i}" for i in range(50)]
        
        # Check each IP in three formats: string, bytes, IP object
        for ip_str in test_ips:
            fw.check(ip_str)
            fw.check(ipaddress.IPv4Address(ip_str).packed)
            fw.check(ipaddress.IPv4Address(ip_str))
        
        cache_info = fw._check_cached.cache_info()
        
        # Should have 50 misses (one per unique IP) and 100 hits (2 additional checks per IP)
        self.assertEqual(cache_info.misses, 50)
        self.assertEqual(cache_info.hits, 100)
        
        # Hit rate should be 66.7% (100 hits / 150 total checks)
        hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses)
        self.assertGreater(hit_rate, 0.65, "Cache hit rate should be > 65%")


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
