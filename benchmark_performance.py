#!/usr/bin/env python3
"""Performance benchmark for Agentic RedTeam Radar."""

import asyncio
import time
from agentic_redteam import RadarScanner, create_mock_agent

async def run_benchmark():
    """Run comprehensive performance benchmarks."""
    print('🚀 PERFORMANCE BENCHMARK')
    print('=' * 50)
    
    scanner = RadarScanner()
    
    # Single scan benchmark
    agent = create_mock_agent('bench-agent')
    start = time.time()
    result = await scanner.scan(agent)
    single_time = time.time() - start
    print(f'✅ Single Scan: {single_time:.2f}s ({len(result.vulnerabilities)} vulnerabilities)')
    
    # Multi-agent benchmark (5 agents)
    agents = [create_mock_agent(f'agent-{i}') for i in range(5)]
    start = time.time()
    results = await scanner.scan_multiple(agents, auto_scale=True)
    multi_time = time.time() - start
    total_vulns = sum(len(r.vulnerabilities) for r in results.values())
    print(f'✅ Multi-Agent (5): {multi_time:.2f}s ({total_vulns} total vulnerabilities)')
    
    # Scalability test (10 agents)
    agents_10 = [create_mock_agent(f'scale-{i}') for i in range(10)]
    start = time.time()
    results_10 = await scanner.scan_multiple(agents_10, auto_scale=True)
    scale_time = time.time() - start
    total_vulns_10 = sum(len(r.vulnerabilities) for r in results_10.values())
    print(f'✅ Scalability (10): {scale_time:.2f}s ({total_vulns_10} total vulnerabilities)')
    
    # Cache performance test
    print('\n💾 CACHE PERFORMANCE TEST')
    print('=' * 30)
    
    # First scan (cache miss)
    cache_agent = create_mock_agent('cache-test')
    start = time.time()
    result1 = await scanner.scan(cache_agent, use_cache=True)
    cache_miss_time = time.time() - start
    
    # Second scan (cache hit)
    start = time.time()
    result2 = await scanner.scan(cache_agent, use_cache=True)
    cache_hit_time = time.time() - start
    
    print(f'✅ Cache Miss: {cache_miss_time:.2f}s')
    print(f'✅ Cache Hit: {cache_hit_time:.2f}s')
    print(f'✅ Cache Speedup: {cache_miss_time/cache_hit_time:.1f}x faster')
    
    # Performance report
    print('\n📊 PERFORMANCE REPORT')
    print('=' * 30)
    perf_report = scanner.get_performance_report()
    
    print(f"✅ Scanner Health: {perf_report['scanner_metrics']['is_healthy']}")
    print(f"✅ Total Scans: {perf_report['scanner_metrics']['total_scans']}")
    print(f"✅ Error Rate: {perf_report['scanner_metrics']['error_rate']:.1%}")
    print(f"✅ Throughput: {5/multi_time:.1f} agents/sec")
    print(f"✅ Scalability: {10/scale_time:.1f} agents/sec (10 agents)")
    
    # Health status
    health = scanner.get_health_status()
    print(f"✅ System Status: {health.get('status', 'unknown')}")
    
    # Quality gates validation
    print('\n🎯 QUALITY GATES VALIDATION')
    print('=' * 40)
    
    quality_passed = True
    
    # Performance gates
    if single_time > 2.0:
        print('❌ FAIL: Single scan too slow (>2.0s)')
        quality_passed = False
    else:
        print(f'✅ PASS: Single scan performance ({single_time:.2f}s ≤ 2.0s)')
    
    if multi_time > 5.0:
        print('❌ FAIL: Multi-agent scan too slow (>5.0s)')
        quality_passed = False
    else:
        print(f'✅ PASS: Multi-agent performance ({multi_time:.2f}s ≤ 5.0s)')
    
    # Cache efficiency gate
    cache_efficiency = cache_hit_time / cache_miss_time
    if cache_efficiency > 0.1:  # Cache hit should be <10% of cache miss time
        print('❌ FAIL: Cache efficiency too low')
        quality_passed = False
    else:
        print(f'✅ PASS: Cache efficiency ({cache_efficiency:.1%} ≤ 10%)')
    
    # Error rate gate
    error_rate = perf_report['scanner_metrics']['error_rate']
    if error_rate > 0.05:  # <5% error rate
        print(f'❌ FAIL: Error rate too high ({error_rate:.1%} > 5%)')
        quality_passed = False
    else:
        print(f'✅ PASS: Error rate acceptable ({error_rate:.1%} ≤ 5%)')
    
    # Health gate
    if not perf_report['scanner_metrics']['is_healthy']:
        print('❌ FAIL: Scanner unhealthy')
        quality_passed = False
    else:
        print('✅ PASS: Scanner healthy')
    
    print(f'\n🎯 OVERALL QUALITY GATE: {"✅ PASSED" if quality_passed else "❌ FAILED"}')
    
    # Cleanup
    await scanner.cleanup_resources()
    
    return quality_passed

if __name__ == '__main__':
    result = asyncio.run(run_benchmark())
    exit(0 if result else 1)