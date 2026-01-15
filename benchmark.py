#!/usr/bin/env python3
"""
Comprehensive benchmark suite for CIDARTHA5 caching strategies.

Tests all 4 caching strategies across multiple workload patterns:
- String lookups
- Bytes lookups
- Mixed string/bytes lookups
- High cardinality (>4096 distinct IPs)
- Cache-friendly (repeated IPs)
"""

import time
import random
import socket
import statistics
from typing import List, Tuple, Dict
from CIDARTHA4 import CIDARTHA as CIDARTHA4
from CIDARTHA5 import CIDARTHA as CIDARTHA5, CIDARTHAConfig


def generate_test_ips(count: int, ipv4_ratio: float = 1.0) -> List[str]:
    """Generate random test IP addresses."""
    ips = []
    ipv4_count = int(count * ipv4_ratio)
    ipv6_count = count - ipv4_count
    
    # Generate IPv4 addresses
    for _ in range(ipv4_count):
        ip = f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        ips.append(ip)
    
    # Generate IPv6 addresses
    for _ in range(ipv6_count):
        parts = [f"{random.randint(0, 65535):x}" for _ in range(8)]
        ip = ":".join(parts)
        ips.append(ip)
    
    return ips


def generate_cidr_blocks(count: int, ipv4_ratio: float = 1.0) -> List[str]:
    """Generate random CIDR blocks."""
    cidrs = []
    ipv4_count = int(count * ipv4_ratio)
    ipv6_count = count - ipv4_count
    
    # Generate IPv4 CIDR blocks
    for _ in range(ipv4_count):
        ip = f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.0"
        prefix = random.choice([24, 25, 26, 27, 28])
        cidrs.append(f"{ip}/{prefix}")
    
    # Generate IPv6 CIDR blocks
    for _ in range(ipv6_count):
        parts = [f"{random.randint(0, 65535):x}" for _ in range(4)]
        ip = ":".join(parts) + "::"
        prefix = random.choice([48, 56, 64])
        cidrs.append(f"{ip}/{prefix}")
    
    return cidrs


def convert_ips_to_bytes(ips: List[str]) -> List[bytes]:
    """Convert IP strings to bytes."""
    result = []
    for ip in ips:
        try:
            result.append(socket.inet_pton(socket.AF_INET, ip))
        except OSError:
            try:
                result.append(socket.inet_pton(socket.AF_INET6, ip))
            except OSError:
                pass
    return result


class BenchmarkResult:
    """Store benchmark results."""
    def __init__(self, name: str):
        self.name = name
        self.total_time = 0.0
        self.operations = 0
        self.throughput = 0.0
        self.avg_latency_us = 0.0
        self.median_latency_us = 0.0
        self.p95_latency_us = 0.0
        self.p99_latency_us = 0.0
        self.cache_info = {}
        self.latencies = []
    
    def calculate_stats(self):
        """Calculate statistics from latencies."""
        if self.latencies:
            self.avg_latency_us = statistics.mean(self.latencies)
            self.median_latency_us = statistics.median(self.latencies)
            sorted_lat = sorted(self.latencies)
            self.p95_latency_us = sorted_lat[int(len(sorted_lat) * 0.95)]
            self.p99_latency_us = sorted_lat[int(len(sorted_lat) * 0.99)]
    
    def __str__(self):
        s = f"\n{'='*70}\n"
        s += f"{self.name}\n"
        s += f"{'='*70}\n"
        s += f"Operations:       {self.operations:,}\n"
        s += f"Total Time:       {self.total_time:.4f} seconds\n"
        s += f"Throughput:       {self.throughput:,.0f} ops/sec\n"
        s += f"Avg Latency:      {self.avg_latency_us:.2f} μs\n"
        s += f"Median Latency:   {self.median_latency_us:.2f} μs\n"
        s += f"P95 Latency:      {self.p95_latency_us:.2f} μs\n"
        s += f"P99 Latency:      {self.p99_latency_us:.2f} μs\n"
        
        if self.cache_info:
            s += f"\nCache Statistics:\n"
            strategy = self.cache_info.get('strategy', 'N/A')
            s += f"  Strategy:       {strategy}\n"
            
            if strategy == "none":
                s += f"  Status:         No caching enabled\n"
            elif strategy == "simple" or strategy == "normalized":
                if 'hits' in self.cache_info:
                    hits = self.cache_info['hits']
                    misses = self.cache_info['misses']
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    s += f"  Hits:           {hits:,}\n"
                    s += f"  Misses:         {misses:,}\n"
                    s += f"  Hit Rate:       {hit_rate:.2f}%\n"
                    s += f"  Current Size:   {self.cache_info.get('currsize', 0):,}\n"
                    s += f"  Max Size:       {self.cache_info.get('maxsize', 0):,}\n"
            elif strategy == "dual":
                if 'normalize_cache' in self.cache_info:
                    norm = self.cache_info['normalize_cache']
                    lookup = self.cache_info['lookup_cache']
                    
                    norm_total = norm['hits'] + norm['misses']
                    norm_hit_rate = (norm['hits'] / norm_total * 100) if norm_total > 0 else 0
                    
                    lookup_total = lookup['hits'] + lookup['misses']
                    lookup_hit_rate = (lookup['hits'] / lookup_total * 100) if lookup_total > 0 else 0
                    
                    s += f"  Normalize Cache:\n"
                    s += f"    Hits:         {norm['hits']:,}\n"
                    s += f"    Misses:       {norm['misses']:,}\n"
                    s += f"    Hit Rate:     {norm_hit_rate:.2f}%\n"
                    s += f"    Size:         {norm['currsize']:,}/{norm['maxsize']:,}\n"
                    s += f"  Lookup Cache:\n"
                    s += f"    Hits:         {lookup['hits']:,}\n"
                    s += f"    Misses:       {lookup['misses']:,}\n"
                    s += f"    Hit Rate:     {lookup_hit_rate:.2f}%\n"
                    s += f"    Size:         {lookup['currsize']:,}/{lookup['maxsize']:,}\n"
        
        return s


def benchmark_workload(cidartha, ips, name: str, warmup: int = 100) -> BenchmarkResult:
    """Benchmark a workload."""
    result = BenchmarkResult(name)
    
    # Warmup
    for ip in ips[:warmup]:
        cidartha.check(ip)
    
    # Clear cache after warmup for fair comparison
    if hasattr(cidartha, 'clear_cache'):
        cidartha.clear_cache()
    
    # Actual benchmark
    latencies = []
    start_time = time.perf_counter()
    
    for ip in ips:
        op_start = time.perf_counter()
        cidartha.check(ip)
        op_end = time.perf_counter()
        latencies.append((op_end - op_start) * 1_000_000)  # Convert to microseconds
    
    end_time = time.perf_counter()
    
    result.total_time = end_time - start_time
    result.operations = len(ips)
    result.throughput = result.operations / result.total_time
    result.latencies = latencies
    result.calculate_stats()
    
    # Get cache info
    if hasattr(cidartha, 'get_cache_info'):
        result.cache_info = cidartha.get_cache_info()
    
    return result


def run_benchmarks():
    """Run comprehensive benchmark suite."""
    print("="*70)
    print("CIDARTHA5 Caching Strategy Benchmark Suite")
    print("="*70)
    
    # Configuration
    num_cidrs = 1000
    num_lookups = 50000
    
    print(f"\nSetup:")
    print(f"  CIDR Blocks:    {num_cidrs:,}")
    print(f"  Lookup Operations: {num_lookups:,}")
    
    # Generate test data
    print("\nGenerating test data...")
    cidrs = generate_cidr_blocks(num_cidrs)
    
    # Different workload patterns
    workloads = {
        "Low Cardinality (100 unique IPs, repeated)": generate_test_ips(100) * (num_lookups // 100),
        "Medium Cardinality (1000 unique IPs, repeated)": generate_test_ips(1000) * (num_lookups // 1000),
        "High Cardinality (10000 unique IPs)": generate_test_ips(num_lookups),
    }
    
    # Strategies to test
    strategies = [
        ("none", "No Cache"),
        ("simple", "Simple LRU (No Normalization)"),
        ("normalized", "Normalized LRU (Pre-convert to bytes)"),
        ("dual", "Dual LRU (Separate normalize + lookup)"),
    ]
    
    all_results = {}
    
    # Test each strategy
    for strategy_id, strategy_name in strategies:
        print(f"\n{'='*70}")
        print(f"Testing Strategy: {strategy_name}")
        print(f"{'='*70}")
        
        all_results[strategy_id] = {}
        
        for workload_name, workload_ips in workloads.items():
            print(f"\nWorkload: {workload_name}")
            print(f"  Setting up CIDARTHA...")
            
            # Create CIDARTHA with this strategy
            config = CIDARTHAConfig(cache_strategy=strategy_id, cache_size=4096)
            fw = CIDARTHA5(config=config)
            fw.batch_insert(cidrs)
            
            print(f"  Running benchmark...")
            
            # Test with string inputs
            result = benchmark_workload(fw, workload_ips, 
                                       f"{strategy_name} - {workload_name} (strings)")
            all_results[strategy_id][workload_name + " (strings)"] = result
            print(result)
            
            # Test with bytes inputs
            workload_bytes = convert_ips_to_bytes(workload_ips)
            if hasattr(fw, 'clear_cache'):
                fw.clear_cache()
            
            result = benchmark_workload(fw, workload_bytes,
                                       f"{strategy_name} - {workload_name} (bytes)")
            all_results[strategy_id][workload_name + " (bytes)"] = result
            print(result)
            
            # Test with mixed inputs (50/50 strings and bytes)
            mixed_workload = []
            for i in range(len(workload_ips)):
                if i % 2 == 0:
                    mixed_workload.append(workload_ips[i])
                else:
                    if i < len(workload_bytes):
                        mixed_workload.append(workload_bytes[i])
            
            if hasattr(fw, 'clear_cache'):
                fw.clear_cache()
            
            result = benchmark_workload(fw, mixed_workload,
                                       f"{strategy_name} - {workload_name} (mixed)")
            all_results[strategy_id][workload_name + " (mixed)"] = result
            print(result)
    
    # Test CIDARTHA4 for comparison
    print(f"\n{'='*70}")
    print(f"Testing CIDARTHA4 (Legacy) for Comparison")
    print(f"{'='*70}")
    
    all_results['cidartha4'] = {}
    
    for workload_name, workload_ips in workloads.items():
        print(f"\nWorkload: {workload_name}")
        print(f"  Setting up CIDARTHA4...")
        
        fw4 = CIDARTHA4()
        fw4.batch_insert(cidrs)
        
        print(f"  Running benchmark...")
        
        # Test with string inputs
        result = benchmark_workload(fw4, workload_ips,
                                   f"CIDARTHA4 - {workload_name} (strings)")
        all_results['cidartha4'][workload_name + " (strings)"] = result
        print(result)
        
        # Test with bytes inputs
        workload_bytes = convert_ips_to_bytes(workload_ips)
        result = benchmark_workload(fw4, workload_bytes,
                                   f"CIDARTHA4 - {workload_name} (bytes)")
        all_results['cidartha4'][workload_name + " (bytes)"] = result
        print(result)
    
    # Print comparison summary
    print("\n" + "="*70)
    print("SUMMARY: Throughput Comparison (ops/sec)")
    print("="*70)
    
    print(f"\n{'Strategy':<30} {'Low Card':<15} {'Med Card':<15} {'High Card':<15}")
    print("-"*70)
    
    for strategy_id, strategy_name in strategies + [("cidartha4", "CIDARTHA4 (Legacy)")]:
        if strategy_id in all_results:
            low = all_results[strategy_id].get("Low Cardinality (100 unique IPs, repeated) (strings)")
            med = all_results[strategy_id].get("Medium Cardinality (1000 unique IPs, repeated) (strings)")
            high = all_results[strategy_id].get("High Cardinality (10000 unique IPs) (strings)")
            
            low_tput = f"{low.throughput:,.0f}" if low else "N/A"
            med_tput = f"{med.throughput:,.0f}" if med else "N/A"
            high_tput = f"{high.throughput:,.0f}" if high else "N/A"
            
            print(f"{strategy_name:<30} {low_tput:<15} {med_tput:<15} {high_tput:<15}")
    
    print("\n" + "="*70)
    print("SUMMARY: Average Latency (μs)")
    print("="*70)
    
    print(f"\n{'Strategy':<30} {'Low Card':<15} {'Med Card':<15} {'High Card':<15}")
    print("-"*70)
    
    for strategy_id, strategy_name in strategies + [("cidartha4", "CIDARTHA4 (Legacy)")]:
        if strategy_id in all_results:
            low = all_results[strategy_id].get("Low Cardinality (100 unique IPs, repeated) (strings)")
            med = all_results[strategy_id].get("Medium Cardinality (1000 unique IPs, repeated) (strings)")
            high = all_results[strategy_id].get("High Cardinality (10000 unique IPs) (strings)")
            
            low_lat = f"{low.avg_latency_us:.2f}" if low else "N/A"
            med_lat = f"{med.avg_latency_us:.2f}" if med else "N/A"
            high_lat = f"{high.avg_latency_us:.2f}" if high else "N/A"
            
            print(f"{strategy_name:<30} {low_lat:<15} {med_lat:<15} {high_lat:<15}")
    
    print("\n" + "="*70)
    print("Benchmark Complete!")
    print("="*70)
    
    return all_results


if __name__ == "__main__":
    results = run_benchmarks()
