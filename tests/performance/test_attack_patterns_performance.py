"""Performance tests for attack pattern components."""

import asyncio
import time
from typing import List, Dict, Any, Generator
import pytest
import random
import string
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock


class MockAttackPattern:
    """Mock attack pattern for performance testing."""
    
    def __init__(self, name: str, complexity: int = 1):
        self.name = name
        self.complexity = complexity
        self.generation_count = 0
        self.evaluation_count = 0
    
    def generate_payloads(self, count: int = 10) -> List[str]:
        """Generate attack payloads."""
        self.generation_count += count
        
        # Simulate payload generation time based on complexity
        time.sleep(0.001 * self.complexity)
        
        payloads = []
        for i in range(count):
            # Generate random payload
            base_payload = f"{self.name}_payload_{i}"
            if self.complexity > 1:
                # Add complexity
                suffix = ''.join(random.choices(string.ascii_letters, k=self.complexity * 10))
                base_payload += f"_{suffix}"
            payloads.append(base_payload)
        
        return payloads
    
    def evaluate_response(self, response: str) -> Dict[str, Any]:
        """Evaluate attack response."""
        self.evaluation_count += 1
        
        # Simulate evaluation time
        time.sleep(0.001 * self.complexity)
        
        # Mock evaluation result
        return {
            'success': len(response) > 50,
            'confidence': random.uniform(0.1, 0.9),
            'evidence': response[:100] if len(response) > 100 else response,
            'severity': random.choice(['low', 'medium', 'high'])
        }


class MockPatternRegistry:
    """Mock pattern registry for testing."""
    
    def __init__(self):
        self.patterns = {
            'prompt_injection': MockAttackPattern('prompt_injection', complexity=2),
            'info_disclosure': MockAttackPattern('info_disclosure', complexity=1),
            'policy_bypass': MockAttackPattern('policy_bypass', complexity=3),
            'tool_abuse': MockAttackPattern('tool_abuse', complexity=2),
            'jailbreak': MockAttackPattern('jailbreak', complexity=4),
        }
    
    def get_pattern(self, name: str) -> MockAttackPattern:
        """Get pattern by name."""
        return self.patterns.get(name)
    
    def get_all_patterns(self) -> List[MockAttackPattern]:
        """Get all patterns."""
        return list(self.patterns.values())
    
    def get_patterns_by_category(self, category: str) -> List[MockAttackPattern]:
        """Get patterns by category."""
        # Mock categorization
        if category == 'injection':
            return [self.patterns['prompt_injection'], self.patterns['jailbreak']]
        elif category == 'disclosure':
            return [self.patterns['info_disclosure']]
        else:
            return self.get_all_patterns()


@pytest.mark.performance
@pytest.mark.benchmark
class TestAttackPatternPerformance:
    """Performance tests for attack patterns."""
    
    @pytest.fixture
    def pattern_registry(self):
        """Provide pattern registry."""
        return MockPatternRegistry()
    
    @pytest.fixture
    def simple_pattern(self):
        """Provide simple attack pattern."""
        return MockAttackPattern('simple_test', complexity=1)
    
    @pytest.fixture
    def complex_pattern(self):
        """Provide complex attack pattern."""
        return MockAttackPattern('complex_test', complexity=5)
    
    def test_payload_generation_performance(
        self, simple_pattern, benchmark_config, performance_monitor
    ):
        """Test payload generation performance."""
        payload_counts = [10, 50, 100, 200]
        generation_times = []
        
        for count in payload_counts:
            start_time = time.perf_counter()
            payloads = simple_pattern.generate_payloads(count)
            end_time = time.perf_counter()
            
            generation_time = end_time - start_time
            generation_times.append(generation_time)
            
            # Verify payloads
            assert len(payloads) == count
            assert all(isinstance(p, str) for p in payloads)
        
        # Performance should scale linearly
        avg_time_per_payload = sum(generation_times) / sum(payload_counts)
        assert avg_time_per_payload < 0.01  # Less than 10ms per payload
        
        print(f"Average time per payload: {avg_time_per_payload*1000:.2f}ms")
    
    def test_batch_payload_generation(
        self, pattern_registry, performance_monitor, performance_thresholds
    ):
        """Test batch payload generation across patterns."""
        all_patterns = pattern_registry.get_all_patterns()
        batch_size = 50
        
        start_time = time.perf_counter()
        
        # Generate payloads for all patterns
        all_payloads = {}
        for pattern in all_patterns:
            payloads = pattern.generate_payloads(batch_size)
            all_payloads[pattern.name] = payloads
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Verify performance
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert len(all_payloads) == len(all_patterns)
        assert all(len(payloads) == batch_size for payloads in all_payloads.values())
        
        total_payloads = sum(len(payloads) for payloads in all_payloads.values())
        throughput = total_payloads / execution_time
        
        print(f"Batch generation throughput: {throughput:.2f} payloads/second")
    
    def test_response_evaluation_performance(
        self, simple_pattern, performance_monitor
    ):
        """Test response evaluation performance."""
        # Generate test responses of varying lengths
        responses = [
            "Short response",
            "Medium length response with some content to analyze for patterns",
            "Very long response " * 50,  # 950+ characters
            "Response with special chars: !@#$%^&*()_+{}[]|\\:;\"'<>?,./",
        ]
        
        evaluation_times = []
        
        for response in responses:
            start_time = time.perf_counter()
            result = simple_pattern.evaluate_response(response)
            end_time = time.perf_counter()
            
            evaluation_time = end_time - start_time
            evaluation_times.append(evaluation_time)
            
            # Verify evaluation result structure
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'confidence' in result
            assert 'evidence' in result
            assert 'severity' in result
        
        # Performance should be consistent regardless of response length
        max_evaluation_time = max(evaluation_times)
        assert max_evaluation_time < 0.1  # Less than 100ms per evaluation
        
        avg_evaluation_time = sum(evaluation_times) / len(evaluation_times)
        print(f"Average evaluation time: {avg_evaluation_time*1000:.2f}ms")
    
    def test_concurrent_pattern_execution(
        self, pattern_registry, benchmark_config, performance_monitor
    ):
        """Test concurrent pattern execution performance."""
        patterns = pattern_registry.get_all_patterns()
        
        def execute_pattern(pattern):
            """Execute a pattern (generate + evaluate)."""
            payloads = pattern.generate_payloads(10)
            results = []
            for payload in payloads:
                # Simulate response
                response = f"Mock response to {payload}"
                evaluation = pattern.evaluate_response(response)
                results.append({
                    'payload': payload,
                    'response': response,
                    'evaluation': evaluation
                })
            return results
        
        # Sequential execution
        start_time = time.perf_counter()
        sequential_results = []
        for pattern in patterns:
            results = execute_pattern(pattern)
            sequential_results.append(results)
        sequential_time = time.perf_counter() - start_time
        
        # Concurrent execution
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=len(patterns)) as executor:
            futures = [executor.submit(execute_pattern, pattern) for pattern in patterns]
            concurrent_results = [future.result() for future in futures]
        concurrent_time = time.perf_counter() - start_time
        
        # Verify results
        assert len(concurrent_results) == len(sequential_results)
        assert all(len(results) == 10 for results in concurrent_results)
        
        # Concurrent should be faster
        speedup = sequential_time / concurrent_time
        assert speedup > 1.2  # At least 20% improvement
        
        print(f"Concurrent execution speedup: {speedup:.2f}x")
        print(f"Sequential time: {sequential_time:.3f}s")
        print(f"Concurrent time: {concurrent_time:.3f}s")
    
    def test_pattern_complexity_scaling(self, performance_monitor):
        """Test how performance scales with pattern complexity."""
        complexities = [1, 2, 3, 4, 5]
        generation_times = []
        evaluation_times = []
        
        for complexity in complexities:
            pattern = MockAttackPattern(f'complexity_{complexity}', complexity)
            
            # Test payload generation
            start_time = time.perf_counter()
            payloads = pattern.generate_payloads(20)
            generation_time = time.perf_counter() - start_time
            generation_times.append(generation_time)
            
            # Test response evaluation
            start_time = time.perf_counter()
            for _ in range(20):
                pattern.evaluate_response("test response for evaluation")
            evaluation_time = time.perf_counter() - start_time
            evaluation_times.append(evaluation_time)
        
        # Verify scaling is reasonable (should be roughly linear)
        # Higher complexity should take more time, but not exponentially
        for i in range(1, len(complexities)):
            gen_ratio = generation_times[i] / generation_times[0]
            eval_ratio = evaluation_times[i] / evaluation_times[0]
            
            # Should not be more than 10x slower for 5x complexity
            assert gen_ratio < 10.0
            assert eval_ratio < 10.0
        
        print("Generation time scaling:", [f"{t:.4f}s" for t in generation_times])
        print("Evaluation time scaling:", [f"{t:.4f}s" for t in evaluation_times])


@pytest.mark.performance
@pytest.mark.memory_intensive
class TestPatternMemoryUsage:
    """Memory usage tests for attack patterns."""
    
    def test_large_payload_memory_efficiency(self, performance_monitor):
        """Test memory efficiency with large payloads."""
        pattern = MockAttackPattern('memory_test', complexity=1)
        
        # Generate large number of payloads
        large_batch_sizes = [100, 500, 1000]
        memory_usage = []
        
        for batch_size in large_batch_sizes:
            initial_memory = performance_monitor.process.memory_info().rss
            
            # Generate payloads
            payloads = pattern.generate_payloads(batch_size)
            
            current_memory = performance_monitor.process.memory_info().rss
            memory_delta = current_memory - initial_memory
            memory_usage.append(memory_delta)
            
            # Clean up
            del payloads
            import gc
            gc.collect()
        
        # Memory usage should scale reasonably
        # Should not use more than 1MB per 100 payloads
        for i, batch_size in enumerate(large_batch_sizes):
            memory_per_payload = memory_usage[i] / batch_size
            assert memory_per_payload < 10 * 1024  # Less than 10KB per payload
        
        print("Memory per payload:", [f"{m/b:.2f} bytes" for m, b in zip(memory_usage, large_batch_sizes)])
    
    def test_pattern_registry_memory_efficiency(self, performance_monitor):
        """Test memory efficiency of pattern registry."""
        initial_memory = performance_monitor.process.memory_info().rss
        
        # Create multiple registries
        registries = []
        for i in range(10):
            registry = MockPatternRegistry()
            # Use the registry to ensure it's not optimized away
            patterns = registry.get_all_patterns()
            assert len(patterns) > 0
            registries.append(registry)
        
        peak_memory = performance_monitor.process.memory_info().rss
        memory_delta = peak_memory - initial_memory
        
        # Clean up
        del registries
        import gc
        gc.collect()
        
        final_memory = performance_monitor.process.memory_info().rss
        memory_cleanup = peak_memory - final_memory
        
        # Memory should be reasonable and cleanable
        assert memory_delta < 50 * 1024 * 1024  # Less than 50MB for 10 registries
        assert memory_cleanup > memory_delta * 0.5  # At least 50% cleanup
        
        print(f"Registry memory usage: {memory_delta / (1024*1024):.2f}MB")
        print(f"Memory cleanup: {memory_cleanup / (1024*1024):.2f}MB")


@pytest.mark.performance
@pytest.mark.cpu_intensive
class TestPatternCPUUsage:
    """CPU usage tests for attack patterns."""
    
    def test_pattern_cpu_efficiency(self, performance_monitor):
        """Test CPU efficiency of pattern operations."""
        pattern = MockAttackPattern('cpu_test', complexity=2)
        
        # Measure CPU usage during intensive operations
        start_cpu = performance_monitor.process.cpu_percent()
        start_time = time.perf_counter()
        
        # Perform CPU-intensive operations
        for _ in range(100):
            payloads = pattern.generate_payloads(20)
            for payload in payloads:
                response = f"response_to_{payload}"
                evaluation = pattern.evaluate_response(response)
                assert evaluation is not None
        
        end_time = time.perf_counter()
        end_cpu = performance_monitor.process.cpu_percent()
        
        execution_time = end_time - start_time
        operations_per_second = (100 * 20) / execution_time  # 100 iterations * 20 payloads
        
        # Should maintain reasonable throughput
        assert operations_per_second > 100  # At least 100 operations per second
        assert execution_time < 30.0  # Should complete within 30 seconds
        
        print(f"Pattern operations per second: {operations_per_second:.2f}")
        print(f"CPU usage change: {end_cpu - start_cpu:.2f}%")
    
    def test_parallel_pattern_cpu_scaling(self, performance_monitor):
        """Test CPU scaling with parallel pattern execution."""
        patterns = [MockAttackPattern(f'parallel_{i}', complexity=1) for i in range(4)]
        
        def cpu_intensive_task(pattern):
            """CPU-intensive pattern task."""
            results = []
            for _ in range(50):
                payloads = pattern.generate_payloads(10)
                for payload in payloads:
                    evaluation = pattern.evaluate_response(f"response_{payload}")
                    results.append(evaluation)
            return results
        
        # Sequential execution
        start_time = time.perf_counter()
        sequential_results = []
        for pattern in patterns:
            results = cpu_intensive_task(pattern)
            sequential_results.extend(results)
        sequential_time = time.perf_counter() - start_time
        
        # Parallel execution
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_task, pattern) for pattern in patterns]
            parallel_results = []
            for future in futures:
                parallel_results.extend(future.result())
        parallel_time = time.perf_counter() - start_time
        
        # Verify CPU scaling
        cpu_speedup = sequential_time / parallel_time
        assert cpu_speedup > 1.5  # Should see some improvement
        assert len(parallel_results) == len(sequential_results)
        
        print(f"CPU scaling speedup: {cpu_speedup:.2f}x")
        print(f"Sequential time: {sequential_time:.3f}s")
        print(f"Parallel time: {parallel_time:.3f}s")


if __name__ == "__main__":
    # Enable running performance tests directly
    pytest.main([__file__, "-v", "-m", "performance"])