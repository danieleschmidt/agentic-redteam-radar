"""Performance tests for the RadarScanner component."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock

# Mock imports for testing without actual dependencies
from tests.performance.conftest import PerformanceMonitor


class MockAgent:
    """Mock agent for performance testing."""
    
    def __init__(self, name: str = "test-agent", response_time: float = 0.1):
        self.name = name
        self.response_time = response_time
        self.call_count = 0
    
    async def query(self, payload: str) -> str:
        """Simulate agent query with configurable response time."""
        self.call_count += 1
        await asyncio.sleep(self.response_time)
        return f"Response to: {payload[:50]}..."


class MockRadarScanner:
    """Mock scanner for performance testing."""
    
    def __init__(self):
        self.attack_patterns = [
            "prompt_injection",
            "info_disclosure", 
            "policy_bypass",
            "tool_abuse"
        ]
    
    async def scan_agent(self, agent: MockAgent, patterns: List[str] = None) -> Dict[str, Any]:
        """Simulate scanning an agent."""
        patterns = patterns or self.attack_patterns
        results = []
        
        for pattern in patterns:
            # Simulate attack pattern execution
            start_time = time.perf_counter()
            response = await agent.query(f"test_{pattern}_payload")
            execution_time = time.perf_counter() - start_time
            
            results.append({
                'pattern': pattern,
                'response': response,
                'execution_time': execution_time,
                'vulnerability_detected': False  # Mock result
            })
        
        return {
            'agent': agent.name,
            'total_patterns': len(patterns),
            'results': results,
            'scan_duration': sum(r['execution_time'] for r in results)
        }


@pytest.mark.performance
@pytest.mark.benchmark
class TestScannerPerformance:
    """Performance tests for scanner operations."""
    
    @pytest.fixture
    def scanner(self):
        """Provide scanner instance."""
        return MockRadarScanner()
    
    @pytest.fixture
    def fast_agent(self):
        """Provide fast-responding agent."""
        return MockAgent("fast-agent", response_time=0.05)
    
    @pytest.fixture
    def slow_agent(self):
        """Provide slow-responding agent."""
        return MockAgent("slow-agent", response_time=0.5)
    
    @pytest.mark.asyncio
    async def test_single_agent_scan_performance(
        self, scanner, fast_agent, performance_monitor, performance_thresholds
    ):
        """Test single agent scanning performance."""
        # Execute scan
        result = await scanner.scan_agent(fast_agent)
        
        # Verify performance
        metrics = performance_monitor.stop()
        assert metrics['execution_time'] < performance_thresholds['scan_single_agent_max_time']
        assert result['scan_duration'] > 0
        assert len(result['results']) == 4  # All attack patterns
    
    @pytest.mark.asyncio
    async def test_batch_agent_scan_performance(
        self, scanner, performance_monitor, performance_thresholds
    ):
        """Test batch agent scanning performance."""
        # Create multiple agents
        agents = [MockAgent(f"agent-{i}", response_time=0.1) for i in range(10)]
        
        # Execute batch scan
        tasks = [scanner.scan_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks)
        
        # Verify performance
        metrics = performance_monitor.stop()
        assert metrics['execution_time'] < performance_thresholds['scan_batch_agents_max_time']
        assert len(results) == 10
        assert all(r['total_patterns'] == 4 for r in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_scan_performance(
        self, scanner, benchmark_config, performance_monitor
    ):
        """Test concurrent scanning performance."""
        agents = [MockAgent(f"concurrent-agent-{i}") for i in range(benchmark_config['concurrent_requests'])]
        
        # Execute concurrent scans
        start_time = time.perf_counter()
        tasks = [scanner.scan_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_time = end_time - start_time
        throughput = len(results) / total_time
        
        # Verify results
        assert len(results) == benchmark_config['concurrent_requests']
        assert throughput > 1.0  # At least 1 scan per second
        
        print(f"Concurrent scan throughput: {throughput:.2f} scans/second")
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self, scanner, load_test_config, performance_monitor, performance_thresholds
    ):
        """Test memory usage under sustained load."""
        agents = [MockAgent(f"load-agent-{i}") for i in range(load_test_config['concurrent_requests'])]
        
        # Run sustained load
        for iteration in range(10):  # Reduced iterations for test
            tasks = [scanner.scan_agent(agent) for agent in agents]
            await asyncio.gather(*tasks)
            
            # Check memory usage periodically
            if iteration % 3 == 0:
                current_metrics = performance_monitor.stop()
                performance_monitor.start()  # Restart monitoring
                
                # Memory should not grow unbounded
                assert current_metrics['memory_delta'] < performance_thresholds['max_memory_usage']
    
    @pytest.mark.benchmark
    def test_attack_pattern_generation_performance(self, benchmark_config):
        """Benchmark attack pattern generation."""
        patterns = []
        
        start_time = time.perf_counter()
        for _ in range(benchmark_config['iterations']):
            # Simulate pattern generation
            pattern = {
                'type': 'prompt_injection',
                'payload': 'ignore previous instructions and ' * 10,
                'variations': [f'variation_{i}' for i in range(5)]
            }
            patterns.append(pattern)
        end_time = time.perf_counter()
        
        # Calculate performance metrics
        total_time = end_time - start_time
        patterns_per_second = len(patterns) / total_time
        
        assert patterns_per_second > 100  # Should generate >100 patterns/second
        print(f"Pattern generation rate: {patterns_per_second:.2f} patterns/second")


@pytest.mark.performance
@pytest.mark.memory_intensive
class TestMemoryPerformance:
    """Memory-focused performance tests."""
    
    @pytest.mark.asyncio
    async def test_large_payload_memory_usage(self, performance_monitor):
        """Test memory usage with large payloads."""
        agent = MockAgent("memory-test-agent")
        
        # Generate large payload
        large_payload = "A" * (1024 * 1024)  # 1MB payload
        
        # Execute with large payload
        response = await agent.query(large_payload)
        
        metrics = performance_monitor.stop()
        
        # Verify memory usage is reasonable
        assert metrics['memory_delta'] < 10 * 1024 * 1024  # Less than 10MB delta
        assert len(response) > 0
    
    def test_memory_leak_detection(self, performance_monitor):
        """Test for memory leaks in repeated operations."""
        initial_memory = performance_monitor.process.memory_info().rss
        
        # Perform repeated operations
        for i in range(100):
            # Simulate operations that might leak memory
            data = [j for j in range(1000)]
            processed = [x * 2 for x in data]
            del data, processed
        
        final_memory = performance_monitor.process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal
        assert memory_growth < 5 * 1024 * 1024  # Less than 5MB growth


@pytest.mark.performance
@pytest.mark.cpu_intensive  
class TestCPUPerformance:
    """CPU-focused performance tests."""
    
    def test_cpu_intensive_analysis(self, performance_monitor):
        """Test CPU usage during intensive analysis."""
        # Simulate CPU-intensive response analysis
        data = np.random.rand(10000, 100)
        
        start_time = time.perf_counter()
        # Simulate analysis operations
        result = np.mean(data, axis=1)
        analysis_scores = np.std(result)
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        
        # Should complete analysis quickly
        assert execution_time < 1.0  # Less than 1 second
        assert analysis_scores >= 0  # Valid result
    
    def test_parallel_processing_performance(self, benchmark_config):
        """Test parallel processing performance."""
        def cpu_task(n):
            """CPU-intensive task."""
            return sum(i * i for i in range(n))
        
        # Sequential execution
        start_time = time.perf_counter()
        sequential_results = [cpu_task(1000) for _ in range(20)]
        sequential_time = time.perf_counter() - start_time
        
        # Parallel execution
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_task, 1000) for _ in range(20)]
            parallel_results = [f.result() for f in as_completed(futures)]
        parallel_time = time.perf_counter() - start_time
        
        # Parallel should be faster (with some tolerance for overhead)
        speedup = sequential_time / parallel_time
        assert speedup > 1.5  # At least 1.5x speedup
        assert len(parallel_results) == len(sequential_results)
        
        print(f"Parallel processing speedup: {speedup:.2f}x")


@pytest.mark.load_test
class TestLoadPerformance: 
    """Load testing scenarios."""
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, load_test_config):
        """Test performance under sustained load."""
        scanner = MockRadarScanner()
        agents = [MockAgent(f"load-agent-{i}") for i in range(load_test_config['concurrent_requests'])]
        
        start_time = time.perf_counter()
        completed_scans = 0
        
        # Run for specified duration
        end_time = start_time + min(load_test_config['duration'], 10)  # Cap at 10 seconds for tests
        
        while time.perf_counter() < end_time:
            # Execute batch of scans
            tasks = [scanner.scan_agent(agent) for agent in agents[:5]]  # Smaller batch for test
            results = await asyncio.gather(*tasks)
            completed_scans += len(results)
        
        actual_duration = time.perf_counter() - start_time
        throughput = completed_scans / actual_duration
        
        # Verify sustained throughput
        assert throughput > 2.0  # At least 2 scans per second
        assert completed_scans > 10  # Minimum number of completed scans
        
        print(f"Sustained load throughput: {throughput:.2f} scans/second")
        print(f"Total scans completed: {completed_scans}")


if __name__ == "__main__":
    # Enable running performance tests directly
    pytest.main([__file__, "-v", "-m", "performance"])