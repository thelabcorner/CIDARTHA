#!/usr/bin/env python3
"""
Benchmark script for CIDARTHA using real-world data from Firehol blocklist-ipsets.
"""

import time
import sys
import os
import urllib.request
import ipaddress
import psutil
from CIDARTHA4 import CIDARTHA

# Firehol blocklist URLs
FIREHOL_URLS = [
    "https://github.com/firehol/blocklist-ipsets/raw/refs/heads/master/firehol_level1.netset",
    "https://github.com/firehol/blocklist-ipsets/raw/refs/heads/master/firehol_level2.netset",
    "https://github.com/firehol/blocklist-ipsets/raw/refs/heads/master/firehol_level3.netset",
    "https://github.com/firehol/blocklist-ipsets/raw/refs/heads/master/firehol_level4.netset",
    "https://github.com/firehol/blocklist-ipsets/raw/refs/heads/master/firehol_webserver.netset",
]


def download_netset(url):
    """Download a .netset file and return list of CIDR blocks."""
    print(f"Downloading {url.split('/')[-1]}...", end=" ", flush=True)
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        # Parse CIDR blocks (skip comments and empty lines)
        cidrs = []
        for line in content.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                try:
                    # Validate it's a valid CIDR
                    ipaddress.ip_network(line, strict=False)
                    cidrs.append(line)
                except ValueError:
                    pass  # Skip invalid entries
        
        print(f"✓ ({len(cidrs)} entries)")
        return cidrs
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_memory_usage():
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def format_time(seconds):
    """Format time in appropriate units."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def format_rate(count, seconds):
    """Format operations per second."""
    rate = count / seconds if seconds > 0 else 0
    if rate >= 1000000:
        return f"{rate / 1000000:.2f} M/s"
    elif rate >= 1000:
        return f"{rate / 1000:.2f} K/s"
    else:
        return f"{rate:.2f} /s"


def benchmark_insert(fw, cidrs):
    """Benchmark insertion operations."""
    print("\n📊 Benchmarking Insertion")
    print("=" * 60)
    
    mem_before = get_memory_usage()
    start_time = time.time()
    
    # Use batch_insert for efficiency
    fw.batch_insert(cidrs)
    
    end_time = time.time()
    mem_after = get_memory_usage()
    
    elapsed = end_time - start_time
    mem_used = mem_after - mem_before
    
    print(f"Total entries inserted: {len(cidrs):,}")
    print(f"Time taken: {format_time(elapsed)}")
    print(f"Insertion rate: {format_rate(len(cidrs), elapsed)}")
    print(f"Average time per insert: {format_time(elapsed / len(cidrs))}")
    print(f"Memory used: {mem_used:.2f} MB")
    print(f"Memory per entry: {mem_used * 1024 / len(cidrs):.2f} KB")
    
    return {
        'count': len(cidrs),
        'time': elapsed,
        'rate': len(cidrs) / elapsed,
        'memory_mb': mem_used,
    }


def benchmark_check(fw, cidrs, num_checks=100000):
    """Benchmark lookup operations."""
    print(f"\n📊 Benchmarking Lookups ({num_checks:,} checks)")
    print("=" * 60)
    
    # Generate test IPs from the CIDR blocks
    test_ips = []
    for cidr in cidrs[:min(len(cidrs), num_checks)]:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            # Use the first IP in the range
            test_ips.append(str(network.network_address))
        except:
            pass
    
    # Add some more to reach target
    while len(test_ips) < num_checks:
        # Add some random IPs that might not be in the list
        test_ips.append(f"8.8.{(len(test_ips) % 256)}.{(len(test_ips) // 256) % 256}")
    
    test_ips = test_ips[:num_checks]
    
    # Warm up cache
    for ip in test_ips[:1000]:
        fw.check(ip)
    
    # Benchmark
    start_time = time.time()
    hits = sum(1 for ip in test_ips if fw.check(ip))
    end_time = time.time()
    
    elapsed = end_time - start_time
    
    print(f"Total checks: {len(test_ips):,}")
    print(f"Hits: {hits:,} ({hits * 100 / len(test_ips):.1f}%)")
    print(f"Misses: {len(test_ips) - hits:,} ({(len(test_ips) - hits) * 100 / len(test_ips):.1f}%)")
    print(f"Time taken: {format_time(elapsed)}")
    print(f"Lookup rate: {format_rate(len(test_ips), elapsed)}")
    print(f"Average time per lookup: {format_time(elapsed / len(test_ips))}")
    
    return {
        'count': len(test_ips),
        'hits': hits,
        'time': elapsed,
        'rate': len(test_ips) / elapsed,
    }


def benchmark_serialization(fw):
    """Benchmark serialization and deserialization."""
    print("\n📊 Benchmarking Serialization")
    print("=" * 60)
    
    # Serialize
    start_time = time.time()
    data = fw.dump()
    serialize_time = time.time() - start_time
    
    data_size = len(data) / 1024 / 1024  # MB
    
    # Deserialize
    start_time = time.time()
    fw2 = CIDARTHA.load(data)
    deserialize_time = time.time() - start_time
    
    print(f"Serialized size: {data_size:.2f} MB")
    print(f"Serialization time: {format_time(serialize_time)}")
    print(f"Deserialization time: {format_time(deserialize_time)}")
    
    return {
        'size_mb': data_size,
        'serialize_time': serialize_time,
        'deserialize_time': deserialize_time,
    }


def run_benchmark():
    """Main benchmark function."""
    print("=" * 60)
    print("CIDARTHA Benchmark Suite")
    print("Using Firehol Blocklist-ipsets (Real-World Data)")
    print("=" * 60)
    
    # Download all netset files
    print("\n📥 Downloading Firehol datasets...")
    all_cidrs = []
    for url in FIREHOL_URLS:
        cidrs = download_netset(url)
        all_cidrs.extend(cidrs)
    
    if not all_cidrs:
        print("\n❌ Error: No CIDR blocks downloaded. Check your internet connection.")
        return 1
    
    print(f"\n✓ Total CIDR blocks loaded: {len(all_cidrs):,}")
    
    # Remove duplicates
    unique_cidrs = list(set(all_cidrs))
    if len(unique_cidrs) < len(all_cidrs):
        print(f"✓ Removed {len(all_cidrs) - len(unique_cidrs):,} duplicates")
    all_cidrs = unique_cidrs
    
    # Create CIDARTHA instance
    print("\n🔧 Initializing CIDARTHA...")
    fw = CIDARTHA()
    
    # Run benchmarks
    insert_results = benchmark_insert(fw, all_cidrs)
    check_results = benchmark_check(fw, all_cidrs)
    serial_results = benchmark_serialization(fw)
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Dataset: Firehol blocklist-ipsets")
    print(f"Total CIDR blocks: {len(all_cidrs):,}")
    print(f"\nInsertion:")
    print(f"  - Rate: {format_rate(insert_results['count'], insert_results['time'])}")
    print(f"  - Memory: {insert_results['memory_mb']:.2f} MB")
    print(f"\nLookup:")
    print(f"  - Rate: {format_rate(check_results['count'], check_results['time'])}")
    print(f"  - Hit rate: {check_results['hits'] * 100 / check_results['count']:.1f}%")
    print(f"\nSerialization:")
    print(f"  - Size: {serial_results['size_mb']:.2f} MB")
    print(f"  - Serialize: {format_time(serial_results['serialize_time'])}")
    print(f"  - Deserialize: {format_time(serial_results['deserialize_time'])}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_benchmark())
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
