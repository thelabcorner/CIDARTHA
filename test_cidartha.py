#!/usr/bin/env python3
"""
Comprehensive unit tests for CIDARTHA4.py
"""
import unittest
import threading
import time
from CIDARTHA4 import CIDARTHA
import ipaddress


class TestCIDARTHABasicOperations(unittest.TestCase):
    """
    Test basic insert, check, and remove operations.
    
    Tests fundamental CIDARTHA operations including IPv4/IPv6 insertion,
    lookups, removal, clearing, and wildcard matching to ensure core
    functionality works correctly.
    """
    
    def setUp(self):
        """Create a fresh CIDARTHA instance for each test."""
        self.fw = CIDARTHA()
    
    def test_insert_and_check_ipv4(self):
        """Test basic IPv4 insert and check."""
        self.fw.insert("192.168.1.0/24")
        self.assertTrue(self.fw.check("192.168.1.1"))
        self.assertTrue(self.fw.check("192.168.1.255"))
        self.assertFalse(self.fw.check("192.168.2.1"))
        self.assertFalse(self.fw.check("10.0.0.1"))
    
    def test_insert_and_check_ipv6(self):
        """Test basic IPv6 insert and check."""
        self.fw.insert("2001:db8::/32")
        self.assertTrue(self.fw.check("2001:db8::1"))
        self.assertTrue(self.fw.check("2001:db8:ffff:ffff:ffff:ffff:ffff:ffff"))
        self.assertFalse(self.fw.check("2001:db9::1"))
        self.assertFalse(self.fw.check("2001:db7::1"))
    
    def test_multiple_inserts(self):
        """Test multiple CIDR insertions."""
        self.fw.insert("10.0.0.0/8")
        self.fw.insert("172.16.0.0/12")
        self.fw.insert("192.168.0.0/16")
        
        self.assertTrue(self.fw.check("10.5.5.5"))
        self.assertTrue(self.fw.check("172.16.0.1"))
        self.assertTrue(self.fw.check("192.168.100.100"))
        self.assertFalse(self.fw.check("8.8.8.8"))
    
    def test_remove_cidr(self):
        """Test removing CIDR blocks."""
        self.fw.insert("192.168.1.0/24")
        self.assertTrue(self.fw.check("192.168.1.1"))
        
        self.fw.remove("192.168.1.0/24")
        self.assertFalse(self.fw.check("192.168.1.1"))
    
    def test_clear(self):
        """Test clearing all entries."""
        self.fw.insert("10.0.0.0/8")
        self.fw.insert("172.16.0.0/12")
        self.assertTrue(self.fw.check("10.0.0.1"))
        
        self.fw.clear()
        self.assertFalse(self.fw.check("10.0.0.1"))
        self.assertFalse(self.fw.check("172.16.0.1"))
    
    def test_wildcard_ipv4(self):
        """Test wildcard matching (0.0.0.0/0)."""
        self.fw.insert("0.0.0.0/0")
        self.assertTrue(self.fw.check("1.2.3.4"))
        self.assertTrue(self.fw.check("192.168.1.1"))
        self.assertTrue(self.fw.check("8.8.8.8"))
    
    def test_wildcard_ipv6(self):
        """Test wildcard matching for IPv6 (::/0)."""
        self.fw.insert("::/0")
        self.assertTrue(self.fw.check("2001:db8::1"))
        self.assertTrue(self.fw.check("::1"))
        self.assertTrue(self.fw.check("fe80::1"))
    
    def test_single_ip(self):
        """Test single IP (/32 for IPv4, /128 for IPv6)."""
        self.fw.insert("192.168.1.100/32")
        self.assertTrue(self.fw.check("192.168.1.100"))
        self.assertFalse(self.fw.check("192.168.1.101"))
        
        self.fw.insert("2001:db8::1/128")
        self.assertTrue(self.fw.check("2001:db8::1"))
        self.assertFalse(self.fw.check("2001:db8::2"))
    
    def test_overlapping_ranges(self):
        """Test overlapping CIDR ranges."""
        self.fw.insert("10.0.0.0/8")
        self.fw.insert("10.10.0.0/16")
        
        # Both should match
        self.assertTrue(self.fw.check("10.5.5.5"))
        self.assertTrue(self.fw.check("10.10.5.5"))
        
        # Remove larger range, smaller should still match
        self.fw.remove("10.0.0.0/8")
        self.assertFalse(self.fw.check("10.5.5.5"))
        self.assertTrue(self.fw.check("10.10.5.5"))


class TestCIDARTHABatchOperations(unittest.TestCase):
    """Test batch operations."""
    
    def setUp(self):
        """Create a fresh CIDARTHA instance for each test."""
        self.fw = CIDARTHA()
    
    def test_batch_insert(self):
        """Test batch insert operation."""
        cidrs = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "203.0.113.0/24",
            "198.51.100.0/24"
        ]
        
        self.fw.batch_insert(cidrs)
        
        self.assertTrue(self.fw.check("10.0.0.1"))
        self.assertTrue(self.fw.check("172.16.0.1"))
        self.assertTrue(self.fw.check("192.168.1.1"))
        self.assertTrue(self.fw.check("203.0.113.1"))
        self.assertTrue(self.fw.check("198.51.100.1"))
        self.assertFalse(self.fw.check("8.8.8.8"))
    
    def test_batch_insert_empty(self):
        """Test batch insert with empty list."""
        self.fw.batch_insert([])
        # Should not raise an error
        self.assertFalse(self.fw.check("192.168.1.1"))
    
    def test_batch_insert_with_comments(self):
        """Test batch insert with comments and whitespace."""
        cidrs = [
            "10.0.0.0/8",
            "  172.16.0.0/12  ",  # With whitespace
            "",  # Empty line
            "192.168.0.0/16"
        ]
        
        self.fw.batch_insert(cidrs)
        
        self.assertTrue(self.fw.check("10.0.0.1"))
        self.assertTrue(self.fw.check("172.16.0.1"))
        self.assertTrue(self.fw.check("192.168.1.1"))


class TestCIDARTHASerialization(unittest.TestCase):
    """Test serialization and deserialization."""
    
    def test_dump_and_load(self):
        """Test dump and load operations."""
        fw1 = CIDARTHA()
        fw1.insert("10.0.0.0/8")
        fw1.insert("192.168.0.0/16")
        fw1.insert("2001:db8::/32")
        
        # Serialize
        data = fw1.dump()
        self.assertIsInstance(data, bytes)
        
        # Deserialize
        fw2 = CIDARTHA.load(data)
        
        # Verify same data
        self.assertTrue(fw2.check("10.0.0.1"))
        self.assertTrue(fw2.check("192.168.1.1"))
        self.assertTrue(fw2.check("2001:db8::1"))
        self.assertFalse(fw2.check("8.8.8.8"))
    
    def test_dump_empty(self):
        """Test dumping an empty trie."""
        fw1 = CIDARTHA()
        data = fw1.dump()
        
        fw2 = CIDARTHA.load(data)
        self.assertFalse(fw2.check("192.168.1.1"))
    
    def test_dump_wildcard(self):
        """Test dumping with wildcard."""
        fw1 = CIDARTHA()
        fw1.insert("0.0.0.0/0")
        
        data = fw1.dump()
        fw2 = CIDARTHA.load(data)
        
        self.assertTrue(fw2.check("1.2.3.4"))
        self.assertTrue(fw2.check("192.168.1.1"))


class TestCIDARTHAEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Create a fresh CIDARTHA instance for each test."""
        self.fw = CIDARTHA()
    
    def test_invalid_ip(self):
        """Test invalid IP addresses."""
        with self.assertRaises(ValueError):
            self.fw.insert("not.an.ip.address")
        
        with self.assertRaises(ValueError):
            self.fw.insert("999.999.999.999/24")
    
    def test_invalid_cidr(self):
        """Test invalid CIDR notation."""
        with self.assertRaises(ValueError):
            self.fw.insert("192.168.1.0/33")  # Invalid prefix for IPv4
        
        with self.assertRaises(ValueError):
            self.fw.insert("2001:db8::/129")  # Invalid prefix for IPv6
    
    def test_remove_nonexistent(self):
        """Test removing non-existent CIDR."""
        # Should not raise an error
        self.fw.remove("192.168.1.0/24")
        self.assertFalse(self.fw.check("192.168.1.1"))
    
    def test_remove_wildcard(self):
        """Test removing wildcard."""
        self.fw.insert("0.0.0.0/0")
        self.assertTrue(self.fw.check("192.168.1.1"))
        
        self.fw.remove("0.0.0.0/0")
        self.assertFalse(self.fw.check("192.168.1.1"))
    
    def test_check_different_formats(self):
        """Test check with different IP formats."""
        self.fw.insert("192.168.1.0/24")
        
        # String
        self.assertTrue(self.fw.check("192.168.1.1"))
        
        # Bytes
        self.assertTrue(self.fw.check(b'\xc0\xa8\x01\x01'))
        
        # IPv4Address object
        ip_obj = ipaddress.IPv4Address("192.168.1.1")
        self.assertTrue(self.fw.check(ip_obj))
        
        # Integer
        ip_int = int(ipaddress.IPv4Address("192.168.1.1"))
        self.assertTrue(self.fw.check(ip_int))
    
    def test_various_prefix_lengths(self):
        """Test various prefix lengths."""
        for prefix in [8, 16, 24, 28, 30, 31, 32]:
            fw = CIDARTHA()
            cidr = f"192.168.1.0/{prefix}"
            fw.insert(cidr)
            
            # Should at least match the network address
            network = ipaddress.ip_network(cidr, strict=False)
            self.assertTrue(fw.check(str(network.network_address)))


class TestCIDARTHAThreadSafety(unittest.TestCase):
    """Test thread safety."""
    
    def test_concurrent_inserts(self):
        """Test concurrent inserts from multiple threads."""
        fw = CIDARTHA()
        num_threads = 10
        entries_per_thread = 50
        
        def worker(thread_id):
            for i in range(entries_per_thread):
                cidr = f"10.{thread_id}.{i}.0/24"
                fw.insert(cidr)
        
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify some entries
        self.assertTrue(fw.check("10.0.0.1"))
        self.assertTrue(fw.check("10.5.25.1"))
        self.assertTrue(fw.check("10.9.49.1"))
    
    def test_concurrent_checks(self):
        """Test concurrent checks from multiple threads."""
        fw = CIDARTHA()
        fw.insert("192.168.0.0/16")
        
        results = []
        
        def worker():
            for i in range(100):
                result = fw.check(f"192.168.{i%256}.1")
                results.append(result)
        
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All should be True
        self.assertEqual(len(results), 1000)
        self.assertTrue(all(results))
    
    def test_concurrent_mixed_operations(self):
        """Test concurrent mixed operations."""
        fw = CIDARTHA()
        
        def inserter():
            for i in range(50):
                fw.insert(f"10.{i}.0.0/16")
                time.sleep(0.001)
        
        def checker():
            for i in range(50):
                fw.check(f"10.{i}.5.5")
                time.sleep(0.001)
        
        def remover():
            time.sleep(0.025)  # Wait a bit before removing
            for i in range(25):
                fw.remove(f"10.{i}.0.0/16")
                time.sleep(0.002)
        
        threads = [
            threading.Thread(target=inserter),
            threading.Thread(target=checker),
            threading.Thread(target=remover),
            threading.Thread(target=inserter),  # Another inserter
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors


class TestCIDARTHACaching(unittest.TestCase):
    """Test LRU caching behavior."""
    
    def test_cached_lookups(self):
        """Test that lookups are cached."""
        fw = CIDARTHA()
        fw.insert("192.168.1.0/24")
        
        # First check - not cached
        result1 = fw.check("192.168.1.1")
        
        # Second check - should use cache
        result2 = fw.check("192.168.1.1")
        
        self.assertEqual(result1, result2)
        self.assertTrue(result1)
    
    def test_cache_invalidation_after_insert(self):
        """Test cache behavior after inserts."""
        fw = CIDARTHA()
        
        # Check before insert
        self.assertFalse(fw.check("192.168.1.1"))
        
        # Insert
        fw.insert("192.168.1.0/24")
        
        # Cache should be invalidated, so check returns True
        result = fw.check("192.168.1.1")
        self.assertTrue(result)


class TestCIDARTHAComplexScenarios(unittest.TestCase):
    """Test complex real-world scenarios."""
    
    def test_large_dataset(self):
        """Test with a larger dataset."""
        fw = CIDARTHA()
        
        # Insert 1000 CIDR blocks
        cidrs = []
        for i in range(256):
            for j in [0, 64, 128, 192]:
                cidrs.append(f"10.{i}.{j}.0/26")
        
        fw.batch_insert(cidrs)
        
        # Verify some matches
        self.assertTrue(fw.check("10.0.0.1"))
        self.assertTrue(fw.check("10.255.192.1"))
        self.assertTrue(fw.check("10.128.128.1"))
        
        # Verify some non-matches (gaps in coverage)
        # With /26 blocks starting at 0, 64, 128, 192
        # IPs in range 32-63 should not match
        self.assertFalse(fw.check("10.0.32.1"))
        self.assertFalse(fw.check("10.0.63.1"))
    
    def test_ipv4_and_ipv6_mixed(self):
        """Test mixed IPv4 and IPv6 entries."""
        fw = CIDARTHA()
        
        fw.insert("10.0.0.0/8")
        fw.insert("192.168.0.0/16")
        fw.insert("2001:db8::/32")
        fw.insert("fe80::/10")
        
        # IPv4 checks
        self.assertTrue(fw.check("10.5.5.5"))
        self.assertTrue(fw.check("192.168.1.1"))
        self.assertFalse(fw.check("8.8.8.8"))
        
        # IPv6 checks
        self.assertTrue(fw.check("2001:db8::1"))
        self.assertTrue(fw.check("fe80::1"))
        self.assertFalse(fw.check("2001:db9::1"))
    
    def test_remove_and_reinsert(self):
        """Test removing and reinserting the same CIDR."""
        fw = CIDARTHA()
        
        for _ in range(5):
            fw.insert("192.168.1.0/24")
            self.assertTrue(fw.check("192.168.1.1"))
            
            fw.remove("192.168.1.0/24")
            self.assertFalse(fw.check("192.168.1.1"))


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHABasicOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHABatchOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHASerialization))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHAEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHAThreadSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHACaching))
    suite.addTests(loader.loadTestsFromTestCase(TestCIDARTHAComplexScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
