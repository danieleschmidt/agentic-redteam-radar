"""Performance testing configuration and fixtures."""

import os
import time
from typing import Dict, Any, Generator
import pytest
import psutil
from memory_profiler import profile


class PerformanceMonitor:
    """Monitor system resources during test execution."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        self.process = psutil.Process(os.getpid())
    
    def start(self) -> None:
        """Start monitoring."""
        self.start_time = time.perf_counter()
        self.start_memory = self.process.memory_info().rss
        self.start_cpu = self.process.cpu_percent()
    
    def stop(self) -> Dict[str, Any]:
        """Stop monitoring and return metrics."""
        end_time = time.perf_counter()
        end_memory = self.process.memory_info().rss
        end_cpu = self.process.cpu_percent()
        
        return {
            'execution_time': end_time - self.start_time,
            'memory_delta': end_memory - self.start_memory,
            'memory_peak': self.process.memory_info().peak_wss if hasattr(self.process.memory_info(), 'peak_wss') else None,
            'cpu_percent': end_cpu,
            'threads_count': self.process.num_threads(),
        }


@pytest.fixture
def performance_monitor() -> Generator[PerformanceMonitor, None, None]:
    """Provide performance monitoring capabilities."""
    monitor = PerformanceMonitor()
    monitor.start()
    yield monitor
    metrics = monitor.stop()
    
    # Store metrics for later analysis
    if not hasattr(pytest, 'performance_results'):
        pytest.performance_results = []
    pytest.performance_results.append(metrics)


@pytest.fixture
def memory_profiler():
    """Enable memory profiling for tests."""
    def wrapper(func):
        return profile(func)
    return wrapper


@pytest.fixture(scope="session")
def performance_thresholds() -> Dict[str, float]:
    """Define performance thresholds for different operations."""
    return {
        'scan_single_agent_max_time': 5.0,  # seconds
        'scan_batch_agents_max_time': 30.0,  # seconds
        'attack_generation_max_time': 1.0,  # seconds
        'response_analysis_max_time': 2.0,  # seconds
        'max_memory_usage': 100 * 1024 * 1024,  # 100MB
        'max_cpu_percent': 80.0,  # 80% CPU
    }


@pytest.fixture
def benchmark_config() -> Dict[str, Any]:
    """Configuration for benchmark tests."""
    return {
        'iterations': int(os.getenv('PERF_ITERATIONS', '100')),
        'warmup_iterations': int(os.getenv('PERF_WARMUP', '10')),
        'timeout': float(os.getenv('PERF_TIMEOUT', '60.0')),
        'parallel_workers': int(os.getenv('PERF_WORKERS', '4')),
    }


@pytest.fixture
def load_test_config() -> Dict[str, Any]:
    """Configuration for load testing."""
    return {
        'concurrent_requests': int(os.getenv('LOAD_CONCURRENT', '10')),
        'total_requests': int(os.getenv('LOAD_TOTAL', '1000')),
        'ramp_up_time': float(os.getenv('LOAD_RAMPUP', '10.0')),
        'duration': float(os.getenv('LOAD_DURATION', '60.0')),
    }


def pytest_configure(config):
    """Configure performance testing markers."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test"
    )
    config.addinivalue_line(
        "markers", "load_test: mark test as a load test"
    )
    config.addinivalue_line(
        "markers", "memory_intensive: mark test as memory intensive"
    )
    config.addinivalue_line(
        "markers", "cpu_intensive: mark test as CPU intensive"
    )


def pytest_runtest_setup(item):
    """Set up performance test environment."""
    if item.get_closest_marker("performance"):
        # Ensure clean environment for performance tests
        import gc
        gc.collect()


def pytest_runtest_teardown(item):
    """Clean up after performance tests."""
    if item.get_closest_marker("performance"):
        import gc
        gc.collect()


def pytest_sessionfinish(session, exitstatus):
    """Generate performance report at session end."""
    if hasattr(pytest, 'performance_results') and pytest.performance_results:
        report_path = "performance_report.json"
        import json
        
        summary = {
            'total_tests': len(pytest.performance_results),
            'average_execution_time': sum(r['execution_time'] for r in pytest.performance_results) / len(pytest.performance_results),
            'max_execution_time': max(r['execution_time'] for r in pytest.performance_results),
            'total_memory_delta': sum(r['memory_delta'] for r in pytest.performance_results),
            'results': pytest.performance_results
        }
        
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nPerformance report saved to: {report_path}")
        print(f"Average execution time: {summary['average_execution_time']:.3f}s")
        print(f"Max execution time: {summary['max_execution_time']:.3f}s")