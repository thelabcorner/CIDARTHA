#!/usr/bin/env python3
"""
Speed comparison test for optimizations.
"""

from CIDARTHA4 import CIDARTHA
import time

def benchmark_lookup_speed():
    """Test lookup speed with cache."""
    print("=" * 60)
    print("LOOKUP SPEED TEST")
    print("=" * 60)
    
    # Create a firewall with many entries
    fw = CIDARTHA()
    cidrs = []
    for i in range(256):
        for j in range(256):
            if j % 4 == 0:  # Every 4th to have reasonable size
                cidrs.append(f"10.{i}.{j}.0/24")
    
    print(f"Loading {len(cidrs):,} CIDR blocks...")
    fw.batch_insert(cidrs)
    print(f"✓ Loaded\n")
    
    # Generate test IPs - mix of hits and misses
    test_ips = []
    for i in range(50000):
        # 70% hits
        if i % 10 < 7:
            test_ips.append(f"10.{i % 256}.{(i % 64) * 4}.{i % 256}")
        else:
            test_ips.append(f"192.168.{i % 256}.{i % 256}")
    
    print(f"Testing with {len(test_ips):,} IP lookups...")
    
    # Cold cache
    fw.check.cache_clear()
    start = time.time()
    hits = sum(1 for ip in test_ips if fw.check(ip))
    cold_time = time.time() - start
    
    print(f"\nCold cache (first run):")
    print(f"  Time: {cold_time:.4f}s")
    print(f"  Rate: {len(test_ips)/cold_time:,.0f} lookups/sec")
    print(f"  Avg: {cold_time*1000000/len(test_ips):.2f} μs/lookup")
    print(f"  Hits: {hits:,} ({hits*100/len(test_ips):.1f}%)")
    
    # Warm cache (same IPs again)
    start = time.time()
    hits = sum(1 for ip in test_ips if fw.check(ip))
    warm_time = time.time() - start
    
    print(f"\nWarm cache (cached results):")
    print(f"  Time: {warm_time:.4f}s")
    print(f"  Rate: {len(test_ips)/warm_time:,.0f} lookups/sec")
    print(f"  Avg: {warm_time*1000000/len(test_ips):.2f} μs/lookup")
    print(f"  Speedup: {cold_time/warm_time:.2f}x faster")
    print()
    print("=" * 60)


def benchmark_insert_optimizations():
    """Test insert optimization."""
    print("\n" + "=" * 60)
    print("INSERT OPTIMIZATION TEST")
    print("=" * 60)
    
    # Create test data
    test_cidrs = [f"10.{i}.{j}.0/24" for i in range(50) for j in range(50)]
    print(f"Test dataset: {len(test_cidrs):,} CIDR blocks\n")
    
    # Test batch insert
    fw = CIDARTHA()
    start = time.time()
    fw.batch_insert(test_cidrs)
    batch_time = time.time() - start
    
    print(f"Batch insert (optimized):")
    print(f"  Time: {batch_time:.4f}s")
    print(f"  Rate: {len(test_cidrs)/batch_time:,.0f} inserts/sec")
    print(f"  Avg: {batch_time*1000000/len(test_cidrs):.2f} μs/insert")
    print()
    print("=" * 60)


def benchmark_memory_efficiency():
    """Test memory efficiency."""
    import psutil
    import os
    
    print("\n" + "=" * 60)
    print("MEMORY EFFICIENCY TEST")
    print("=" * 60)
    
    process = psutil.Process(os.getpid())
    
    # Baseline
    mem_before = process.memory_info().rss / 1024 / 1024
    
    fw = CIDARTHA()
    test_cidrs = [f"10.{i}.{j}.0/24" for i in range(100) for j in range(100)]
    
    print(f"Loading {len(test_cidrs):,} CIDR blocks...")
    fw.batch_insert(test_cidrs)
    
    mem_after = process.memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before
    
    print(f"✓ Loaded\n")
    print(f"Memory usage:")
    print(f"  Total: {mem_used:.2f} MB")
    print(f"  Per entry: {mem_used * 1024 / len(test_cidrs):.2f} KB")
    print(f"  Efficiency: {len(test_cidrs) / mem_used:.0f} entries/MB")
    
    # Test serialization compression
    data = fw.dump()
    compressed_size = len(data) / 1024 / 1024
    compression_ratio = mem_used / compressed_size
    
    print(f"\nSerialization:")
    print(f"  Serialized size: {compressed_size:.2f} MB")
    print(f"  Compression: {compression_ratio:.1f}:1")
    print()
    print("=" * 60)


if __name__ == "__main__":
    benchmark_lookup_speed()
    benchmark_insert_optimizations()
    benchmark_memory_efficiency()
    
    print("\n✓ All speed tests completed successfully!")
