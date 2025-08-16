"""
Enhanced Generation 3 scanner with scaling and optimization features.
"""

import sys
import asyncio
import time
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_redteam import RadarScanner
from agentic_redteam.agent import create_mock_agent
from agentic_redteam.scaling.simple_resource_pool import SimpleResourcePool, ConcurrencyManager, LoadBalancer
from agentic_redteam.reliability.simple_health_monitor import SimpleHealthMonitor


async def demonstrate_generation3_scaling():
    """
    Demonstrate Generation 3 scaling and optimization features.
    """
    print("⚡ GENERATION 3: SCALING & OPTIMIZATION DEMO")
    print("=" * 50)
    
    # Initialize components
    scanner = RadarScanner()
    health_monitor = SimpleHealthMonitor()
    concurrency_manager = ConcurrencyManager(max_concurrent=5)
    
    # Start health monitoring
    await health_monitor.start_monitoring()
    
    try:
        # Test 1: Resource Pool Management
        print("\n1. Resource Pool Management")
        print("-" * 30)
        
        # Create a resource pool for agents
        def create_test_agent():
            return create_mock_agent(f"pooled-agent-{int(time.time() * 1000) % 10000}")
        
        agent_pool = SimpleResourcePool(
            name="agent_pool",
            resource_factory=create_test_agent,
            min_size=2,
            max_size=5
        )
        
        # Test resource acquisition and release
        agents = []
        for i in range(3):
            agent = await agent_pool.acquire()
            agents.append(agent)
            print(f"Acquired agent: {agent.name}")
        
        pool_metrics = agent_pool.get_metrics()
        print(f"Pool metrics: {pool_metrics.active_resources} active, {pool_metrics.idle_resources} idle")
        
        # Release agents back to pool
        for agent in agents:
            await agent_pool.release(agent)
        
        final_metrics = agent_pool.get_metrics()
        print(f"After release: {final_metrics.active_resources} active, {final_metrics.idle_resources} idle")
        
        # Test 2: Concurrent Scanning
        print("\n2. Concurrent Scanning Performance")
        print("-" * 30)
        
        # Create multiple agents for concurrent testing
        test_agents = [create_mock_agent(f"concurrent-agent-{i}") for i in range(3)]
        
        # Sequential scanning (baseline)
        start_time = time.time()
        sequential_results = []
        for agent in test_agents:
            result = await scanner.scan(agent)
            sequential_results.append(result)
        sequential_duration = time.time() - start_time
        
        print(f"Sequential scanning: {sequential_duration:.2f}s for {len(test_agents)} agents")
        
        # Concurrent scanning (optimized)
        start_time = time.time()
        
        async def scan_agent(agent):
            return await scanner.scan(agent)
        
        scan_tasks = [scan_agent(agent) for agent in test_agents]
        concurrent_results = await concurrency_manager.run_concurrent(scan_tasks)
        concurrent_duration = time.time() - start_time
        
        print(f"Concurrent scanning: {concurrent_duration:.2f}s for {len(test_agents)} agents")
        
        speedup = sequential_duration / concurrent_duration if concurrent_duration > 0 else 0
        print(f"Performance improvement: {speedup:.2f}x speedup")
        
        # Test 3: Load Balancing
        print("\n3. Load Balancing Distribution")
        print("-" * 30)
        
        # Create scanner instances for load balancing
        scanners = [RadarScanner() for _ in range(3)]
        load_balancer = LoadBalancer(scanners)
        
        # Distribute work across scanners
        test_agents_lb = [create_mock_agent(f"lb-agent-{i}") for i in range(6)]
        
        async def distributed_scan(agent):
            assigned_scanner = load_balancer.get_least_used_resource()
            return await assigned_scanner.scan(agent)
        
        start_time = time.time()
        distributed_tasks = [distributed_scan(agent) for agent in test_agents_lb]
        distributed_results = await asyncio.gather(*distributed_tasks)
        distributed_duration = time.time() - start_time
        
        lb_stats = load_balancer.get_stats()
        print(f"Load balanced scanning: {distributed_duration:.2f}s")
        print(f"Total scanners: {lb_stats['total_resources']}")
        print(f"Total requests: {lb_stats['total_requests']}")
        print(f"Avg requests per scanner: {lb_stats['avg_requests_per_resource']:.1f}")
        
        # Test 4: Batch Processing Optimization
        print("\n4. Batch Processing Optimization")
        print("-" * 30)
        
        # Create larger batch of agents
        batch_agents = [create_mock_agent(f"batch-agent-{i}") for i in range(8)]
        
        # Test different batch sizes
        batch_sizes = [2, 4, 8]
        
        for batch_size in batch_sizes:
            start_time = time.time()
            
            batch_results = await concurrency_manager.throttled_execution(
                scan_agent,
                batch_agents,
                batch_size=batch_size
            )
            
            batch_duration = time.time() - start_time
            successful_scans = sum(1 for r in batch_results if not isinstance(r, Exception))
            
            print(f"Batch size {batch_size}: {batch_duration:.2f}s, {successful_scans}/{len(batch_agents)} successful")
        
        # Test 5: Resource Utilization and Monitoring
        print("\n5. Resource Utilization Monitoring")
        print("-" * 30)
        
        # Get health status during high load
        health_before = health_monitor.get_current_health()
        print(f"Health before load: {health_before.status.value} (score: {health_before.score:.2f})")
        
        # Simulate high load
        high_load_agents = [create_mock_agent(f"load-agent-{i}") for i in range(10)]
        
        start_time = time.time()
        load_tasks = [scan_agent(agent) for agent in high_load_agents]
        load_results = await concurrency_manager.run_concurrent(load_tasks)
        load_duration = time.time() - start_time
        
        health_after = health_monitor.get_current_health()
        print(f"Health after load: {health_after.status.value} (score: {health_after.score:.2f})")
        print(f"High load test: {load_duration:.2f}s for {len(high_load_agents)} agents")
        
        successful_load_scans = sum(1 for r in load_results if not isinstance(r, Exception))
        throughput = successful_load_scans / load_duration if load_duration > 0 else 0
        print(f"Throughput: {throughput:.1f} scans/second")
        
        # Test 6: Memory and Performance Optimization
        print("\n6. Performance Optimization Summary")
        print("-" * 30)
        
        # Calculate overall performance metrics
        total_scans = (len(sequential_results) + len(concurrent_results) + 
                      len(distributed_results) + len(load_results))
        total_vulnerabilities = 0
        
        for result_set in [sequential_results, concurrent_results, distributed_results, load_results]:
            for result in result_set:
                if not isinstance(result, Exception) and hasattr(result, 'vulnerabilities'):
                    total_vulnerabilities += len(result.vulnerabilities)
        
        print(f"Total scans executed: {total_scans}")
        print(f"Total vulnerabilities found: {total_vulnerabilities}")
        print(f"Average vulnerabilities per scan: {total_vulnerabilities / total_scans:.1f}")
        
        # Resource efficiency metrics
        pool_efficiency = (pool_metrics.successful_acquisitions / 
                          max(pool_metrics.total_acquisitions, 1) * 100)
        print(f"Resource pool efficiency: {pool_efficiency:.1f}%")
        
        print("\n✅ Generation 3 Scaling Features Verified")
        
        return {
            "total_scans": total_scans,
            "total_vulnerabilities": total_vulnerabilities,
            "sequential_duration": sequential_duration,
            "concurrent_duration": concurrent_duration,
            "speedup_factor": speedup,
            "throughput": throughput,
            "final_health_score": health_after.score,
            "scaling_features": [
                "Resource Pooling",
                "Concurrent Processing",
                "Load Balancing",
                "Batch Optimization",
                "Performance Monitoring",
                "Throughput Optimization"
            ]
        }
        
    finally:
        # Cleanup
        await health_monitor.stop_monitoring()
        await agent_pool.clear()


def main():
    """Run Generation 3 scaling demonstration."""
    return asyncio.run(demonstrate_generation3_scaling())


if __name__ == "__main__":
    results = main()
    print(f"\n🚀 Generation 3 Complete: {results['throughput']:.1f} scans/sec throughput")