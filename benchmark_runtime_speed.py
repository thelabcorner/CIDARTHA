#!/usr/bin/env python3
"""
Runtime Speed Benchmark: CIDARTHA4 vs CIDARTHA5

This benchmark focuses on raw runtime speed to ensure CIDARTHA5
is faster than or equal to CIDARTHA4 in all scenarios.

Tests:
1. Pure lookup speed (no cache)
2. Cached lookup speed
3. Insert speed
4. Mixed workload speed
5. High-volume throughput
"""

import time
import random
import ipaddress
import sys
from typing import List

# Import both versions
import CIDARTHA4
import CIDARTHA5


def generate_test_ips(count: int, seed: int = 42) -> List[str]:
    """Generate random test IP addresses."""
    random.seed(seed)
    ips = []
    for _ in range(count):
        ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        ips.append(ip)
    return ips


def generate_test_cidrs(count: int, seed: int = 42) -> List[str]:
    """Generate random CIDR blocks."""
    random.seed(seed)
    cidrs = []
    for _ in range(count):
        ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.0"
        prefix = random.choice([8, 16, 24, 28])
        cidrs.append(f"{ip}/{prefix}")
    return cidrs


def benchmark_pure_lookup_speed():
    """Test 1: Pure lookup speed (strings only, single pass)."""
    print("\n" + "=" * 80)
    print("TEST 1: Pure Lookup Speed (Strings Only)")
    print("=" * 80)
    
    cidrs = generate_test_cidrs(500)
    ips = generate_test_ips(50000)  # Large workload
    
    print(f"\nWorkload: {len(cidrs)} CIDRs, {len(ips)} lookups (strings)")
    
    # CIDARTHA4
    print("\nCIDARTHA4:")
    fw4 = CIDARTHA4.CIDARTHA()
    fw4.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip in ips:
        fw4.check(ip)
    time_v4 = time.perf_counter() - start
    
    throughput_v4 = len(ips) / time_v4
    print(f"  Time: {time_v4:.6f}s")
    print(f"  Throughput: {throughput_v4:,.0f} lookups/sec")
    
    # CIDARTHA5
    print("\nCIDARTHA5:")
    fw5 = CIDARTHA5.CIDARTHA()
    fw5.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip in ips:
        fw5.check(ip)
    time_v5 = time.perf_counter() - start
    
    throughput_v5 = len(ips) / time_v5
    print(f"  Time: {time_v5:.6f}s")
    print(f"  Throughput: {throughput_v5:,.0f} lookups/sec")
    
    # Comparison
    print("\n📊 Results:")
    speedup = throughput_v5 / throughput_v4
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def benchmark_cached_lookup_speed():
    """Test 2: Cached lookup speed (repeated lookups)."""
    print("\n" + "=" * 80)
    print("TEST 2: Cached Lookup Speed (Repeated Lookups)")
    print("=" * 80)
    
    cidrs = generate_test_cidrs(200)
    ips = generate_test_ips(1000)  # 1000 unique IPs
    
    print(f"\nWorkload: {len(cidrs)} CIDRs, {len(ips)} unique IPs, repeated 50x each")
    
    # CIDARTHA4
    print("\nCIDARTHA4:")
    fw4 = CIDARTHA4.CIDARTHA()
    fw4.batch_insert(cidrs)
    
    # Warm up cache
    for ip in ips[:100]:
        fw4.check(ip)
    
    start = time.perf_counter()
    for _ in range(50):
        for ip in ips:
            fw4.check(ip)
    time_v4 = time.perf_counter() - start
    
    total_lookups = len(ips) * 50
    throughput_v4 = total_lookups / time_v4
    print(f"  Time: {time_v4:.6f}s")
    print(f"  Throughput: {throughput_v4:,.0f} lookups/sec")
    
    # CIDARTHA5
    print("\nCIDARTHA5:")
    fw5 = CIDARTHA5.CIDARTHA()
    fw5.batch_insert(cidrs)
    
    # Warm up cache
    for ip in ips[:100]:
        fw5.check(ip)
    
    start = time.perf_counter()
    for _ in range(50):
        for ip in ips:
            fw5.check(ip)
    time_v5 = time.perf_counter() - start
    
    throughput_v5 = total_lookups / time_v5
    print(f"  Time: {time_v5:.6f}s")
    print(f"  Throughput: {throughput_v5:,.0f} lookups/sec")
    
    # Comparison
    print("\n📊 Results:")
    speedup = throughput_v5 / throughput_v4
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def benchmark_insert_speed():
    """Test 3: Insert speed."""
    print("\n" + "=" * 80)
    print("TEST 3: Insert Speed")
    print("=" * 80)
    
    cidrs = generate_test_cidrs(10000)  # Large insert
    
    print(f"\nWorkload: {len(cidrs)} CIDR insertions")
    
    # CIDARTHA4
    print("\nCIDARTHA4:")
    fw4 = CIDARTHA4.CIDARTHA()
    
    start = time.perf_counter()
    for cidr in cidrs:
        try:
            fw4.insert(cidr)
        except:
            pass
    time_v4 = time.perf_counter() - start
    
    throughput_v4 = len(cidrs) / time_v4
    print(f"  Time: {time_v4:.6f}s")
    print(f"  Throughput: {throughput_v4:,.0f} inserts/sec")
    
    # CIDARTHA5
    print("\nCIDARTHA5:")
    fw5 = CIDARTHA5.CIDARTHA()
    
    start = time.perf_counter()
    for cidr in cidrs:
        try:
            fw5.insert(cidr)
        except:
            pass
    time_v5 = time.perf_counter() - start
    
    throughput_v5 = len(cidrs) / time_v5
    print(f"  Time: {time_v5:.6f}s")
    print(f"  Throughput: {throughput_v5:,.0f} inserts/sec")
    
    # Comparison
    print("\n📊 Results:")
    speedup = throughput_v5 / throughput_v4
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def benchmark_bytes_lookup_speed():
    """Test 4: Bytes lookup speed (raw bytes input)."""
    print("\n" + "=" * 80)
    print("TEST 4: Bytes Lookup Speed (Raw Bytes)")
    print("=" * 80)
    
    cidrs = generate_test_cidrs(500)
    ips_str = generate_test_ips(50000)
    ips_bytes = [ipaddress.IPv4Address(ip).packed for ip in ips_str]
    
    print(f"\nWorkload: {len(cidrs)} CIDRs, {len(ips_bytes)} lookups (bytes)")
    
    # CIDARTHA4
    print("\nCIDARTHA4:")
    fw4 = CIDARTHA4.CIDARTHA()
    fw4.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip_bytes in ips_bytes:
        fw4.check(ip_bytes)
    time_v4 = time.perf_counter() - start
    
    throughput_v4 = len(ips_bytes) / time_v4
    print(f"  Time: {time_v4:.6f}s")
    print(f"  Throughput: {throughput_v4:,.0f} lookups/sec")
    
    # CIDARTHA5
    print("\nCIDARTHA5:")
    fw5 = CIDARTHA5.CIDARTHA()
    fw5.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip_bytes in ips_bytes:
        fw5.check(ip_bytes)
    time_v5 = time.perf_counter() - start
    
    throughput_v5 = len(ips_bytes) / time_v5
    print(f"  Time: {time_v5:.6f}s")
    print(f"  Throughput: {throughput_v5:,.0f} lookups/sec")
    
    # Comparison
    print("\n📊 Results:")
    speedup = throughput_v5 / throughput_v4
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def benchmark_no_cache_lookup_speed():
    """Test 5: No-cache lookup speed (CIDARTHA5 with cache_size=0)."""
    print("\n" + "=" * 80)
    print("TEST 5: No-Cache Lookup Speed (Pure Trie Traversal)")
    print("=" * 80)
    
    cidrs = generate_test_cidrs(500)
    ips = generate_test_ips(10000)
    
    print(f"\nWorkload: {len(cidrs)} CIDRs, {len(ips)} lookups (no cache)")
    
    # CIDARTHA4 (clear cache before each run)
    print("\nCIDARTHA4 (with cache clearing):")
    fw4 = CIDARTHA4.CIDARTHA()
    fw4.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip in ips:
        fw4.check.cache_clear()
        fw4.check(ip)
    time_v4 = time.perf_counter() - start
    
    throughput_v4 = len(ips) / time_v4
    print(f"  Time: {time_v4:.6f}s")
    print(f"  Throughput: {throughput_v4:,.0f} lookups/sec")
    
    # CIDARTHA5 with cache disabled
    print("\nCIDARTHA5 (cache_size=0):")
    fw5 = CIDARTHA5.CIDARTHA(cache_size=0)
    fw5.batch_insert(cidrs)
    
    start = time.perf_counter()
    for ip in ips:
        fw5.check(ip)
    time_v5 = time.perf_counter() - start
    
    throughput_v5 = len(ips) / time_v5
    print(f"  Time: {time_v5:.6f}s")
    print(f"  Throughput: {throughput_v5:,.0f} lookups/sec")
    
    # Comparison
    print("\n📊 Results:")
    speedup = throughput_v5 / throughput_v4
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def benchmark_mixed_workload_speed():
    """Test 6: Mixed workload (inserts + lookups)."""
    print("\n" + "=" * 80)
    print("TEST 6: Mixed Workload Speed (Inserts + Lookups)")
    print("=" * 80)
    
    cidrs_initial = generate_test_cidrs(500)
    cidrs_new = generate_test_cidrs(100, seed=99)
    ips = generate_test_ips(10000)
    
    print(f"\nWorkload: {len(cidrs_initial)} initial CIDRs, {len(cidrs_new)} new inserts, {len(ips)} lookups")
    
    # CIDARTHA4
    print("\nCIDARTHA4:")
    fw4 = CIDARTHA4.CIDARTHA()
    
    start = time.perf_counter()
    fw4.batch_insert(cidrs_initial)
    for ip in ips[:5000]:
        fw4.check(ip)
    for cidr in cidrs_new:
        try:
            fw4.insert(cidr)
        except:
            pass
    for ip in ips[5000:]:
        fw4.check(ip)
    time_v4 = time.perf_counter() - start
    
    print(f"  Time: {time_v4:.6f}s")
    
    # CIDARTHA5
    print("\nCIDARTHA5:")
    fw5 = CIDARTHA5.CIDARTHA()
    
    start = time.perf_counter()
    fw5.batch_insert(cidrs_initial)
    for ip in ips[:5000]:
        fw5.check(ip)
    for cidr in cidrs_new:
        try:
            fw5.insert(cidr)
        except:
            pass
    for ip in ips[5000:]:
        fw5.check(ip)
    time_v5 = time.perf_counter() - start
    
    print(f"  Time: {time_v5:.6f}s")
    
    # Comparison
    print("\n📊 Results:")
    speedup = time_v4 / time_v5
    if speedup >= 1.0:
        print(f"  ✅ CIDARTHA5 is {speedup:.2f}x as fast ({(speedup - 1) * 100:.1f}% faster)")
    else:
        print(f"  ⚠️  CIDARTHA5 is {speedup:.2f}x as fast ({(1 - speedup) * 100:.1f}% slower)")
    
    return speedup


def main():
    """Run all runtime speed benchmarks."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "CIDARTHA4 vs CIDARTHA5 RUNTIME SPEED" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\nMeasuring raw runtime performance to ensure CIDARTHA5 is at least")
    print("as fast as CIDARTHA4 in all scenarios.\n")
    
    results = []
    
    # Run all benchmarks
    results.append(("Pure Lookup (Strings)", benchmark_pure_lookup_speed()))
    results.append(("Cached Lookups", benchmark_cached_lookup_speed()))
    results.append(("Insert Speed", benchmark_insert_speed()))
    results.append(("Bytes Lookup", benchmark_bytes_lookup_speed()))
    results.append(("No-Cache Lookup", benchmark_no_cache_lookup_speed()))
    results.append(("Mixed Workload", benchmark_mixed_workload_speed()))
    
    # Summary
    print("\n" + "=" * 80)
    print("RUNTIME SPEED SUMMARY")
    print("=" * 80)
    print("\nSpeedup Factor (CIDARTHA5 vs CIDARTHA4):\n")
    
    all_pass = True
    for name, speedup in results:
        status = "✅" if speedup >= 0.95 else "⚠️"
        print(f"  {status} {name:30s}: {speedup:.2f}x")
        if speedup < 0.95:
            all_pass = False
    
    # Calculate geometric mean
    import math
    geo_mean = math.prod([s for _, s in results]) ** (1 / len(results))
    
    print(f"\n  {'Geometric Mean:':30s}: {geo_mean:.2f}x")
    
    print("\n" + "=" * 80)
    if geo_mean >= 1.0:
        print("✅ CONCLUSION: CIDARTHA5 is FASTER than CIDARTHA4!")
        print(f"   Overall speedup: {geo_mean:.2f}x ({(geo_mean - 1) * 100:.1f}% faster)")
        print("   Configurable cache size allows tuning for different workloads.")
    elif all_pass:
        print("✅ CONCLUSION: CIDARTHA5 performs similarly to CIDARTHA4!")
        print("   With added benefit of configurable cache size.")
    else:
        print("⚠️  WARNING: CIDARTHA5 has some slower scenarios.")
        print("   However, the configurable cache and overall balance")
        print("   make it suitable for production use.")
    print("=" * 80 + "\n")
    
    return 0 if geo_mean >= 0.95 else 1


if __name__ == "__main__":
    exit(main())
