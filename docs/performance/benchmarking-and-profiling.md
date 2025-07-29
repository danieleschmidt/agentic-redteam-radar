# Benchmarking and Profiling Guide

This document provides comprehensive guidelines for benchmarking, profiling, and performance optimization of the Agentic RedTeam Radar security scanner.

## Overview

Performance is critical for a security scanner that needs to test multiple AI agents efficiently. This guide covers:

- **Benchmarking**: Measuring and tracking performance metrics over time
- **Profiling**: Identifying performance bottlenecks and optimization opportunities
- **Optimization**: Systematic approaches to improving performance
- **Monitoring**: Continuous performance monitoring in production

## Performance Goals and SLAs

### Service Level Agreements (SLAs)

| Operation | Target | Maximum | Measurement |
|-----------|--------|---------|-------------|
| Single Agent Scan | < 10s | < 30s | P95 response time |
| Batch Scan (10 agents) | < 60s | < 120s | Total completion time |
| Attack Pattern Generation | < 1s | < 5s | P95 response time |
| Response Analysis | < 2s | < 10s | P95 response time |
| Report Generation | < 5s | < 15s | P95 response time |
| API Response Time | < 500ms | < 2s | P95 response time |

### Resource Utilization Targets

| Resource | Target | Maximum | Context |
|----------|--------|---------|---------|
| Memory Usage | < 512MB | < 2GB | Per scanning process |
| CPU Usage | < 50% | < 80% | Average during scans |
| Database Connections | < 10 | < 50 | Active connections |
| Network Bandwidth | < 10MB/s | < 50MB/s | During intensive scans |

## Benchmarking Framework

### Benchmark Test Structure

```python
# tests/benchmarks/conftest.py
import pytest
import asyncio
from typing import Dict, Any, List
import time
import psutil
import os
from dataclasses import dataclass

@dataclass
class BenchmarkResult:
    """Structured benchmark result data."""
    operation_name: str
    duration_seconds: float
    memory_peak_mb: float
    cpu_percent: float
    iterations: int
    throughput_ops_per_sec: float
    metadata: Dict[str, Any]

class BenchmarkHarness:
    """Advanced benchmarking harness with resource monitoring."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss
    
    async def run_benchmark(
        self, 
        operation, 
        iterations: int = 100,
        warmup_iterations: int = 10,
        metadata: Dict[str, Any] = None
    ) -> BenchmarkResult:
        """Run comprehensive benchmark with resource monitoring."""
        
        # Warmup phase
        print(f"Warming up with {warmup_iterations} iterations...")
        for _ in range(warmup_iterations):
            if asyncio.iscoroutinefunction(operation):
                await operation()
            else:
                operation()
        
        # Collect garbage before measurement
        import gc
        gc.collect()
        
        # Measure baseline resources
        baseline_memory = self.process.memory_info().rss
        
        # Benchmark phase
        print(f"Running benchmark with {iterations} iterations...")
        start_time = time.perf_counter()
        peak_memory = baseline_memory
        cpu_times = []
        
        for i in range(iterations):
            # Monitor resources every 10 iterations
            if i % 10 == 0:
                current_memory = self.process.memory_info().rss
                peak_memory = max(peak_memory, current_memory)
                cpu_times.append(self.process.cpu_percent(interval=None))
            
            # Execute operation
            if asyncio.iscoroutinefunction(operation):
                await operation()
            else:
                operation()
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_duration = end_time - start_time
        avg_cpu = sum(cpu_times) / len(cpu_times) if cpu_times else 0
        peak_memory_mb = (peak_memory - baseline_memory) / (1024 * 1024)
        throughput = iterations / total_duration
        
        return BenchmarkResult(
            operation_name=operation.__name__,
            duration_seconds=total_duration,
            memory_peak_mb=peak_memory_mb,
            cpu_percent=avg_cpu,
            iterations=iterations,
            throughput_ops_per_sec=throughput,
            metadata=metadata or {}
        )

@pytest.fixture
def benchmark_harness():
    """Provide benchmark harness for tests."""
    return BenchmarkHarness()
```

### Core Performance Benchmarks

```python
# tests/benchmarks/test_scanner_benchmarks.py
import pytest
import asyncio
from tests.benchmarks.conftest import BenchmarkHarness
from agentic_redteam.scanner import RadarScanner
from agentic_redteam.agents import MockAgent
from agentic_redteam.patterns import PromptInjectionPattern

class TestScannerBenchmarks:
    """Comprehensive scanner performance benchmarks."""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_single_agent_scan_benchmark(self, benchmark_harness):
        """Benchmark single agent scanning performance."""
        
        # Setup
        scanner = RadarScanner()
        agent = MockAgent("benchmark-agent", response_time=0.1)
        
        async def scan_operation():
            return await scanner.scan_agent(agent)
        
        # Run benchmark
        result = await benchmark_harness.run_benchmark(
            scan_operation,
            iterations=50,
            metadata={"agent_type": "mock", "patterns": "all"}
        )
        
        # Assertions
        assert result.throughput_ops_per_sec > 2.0  # At least 2 scans per second
        assert result.memory_peak_mb < 100  # Less than 100MB peak memory
        assert result.duration_seconds < 30  # Complete within 30 seconds
        
        print(f"Single agent scan: {result.throughput_ops_per_sec:.2f} ops/sec")
        print(f"Memory usage: {result.memory_peak_mb:.2f} MB")
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_scan_benchmark(self, benchmark_harness):
        """Benchmark concurrent scanning performance."""
        
        scanner = RadarScanner()
        agents = [MockAgent(f"agent-{i}", response_time=0.05) for i in range(10)]
        
        async def concurrent_scan_operation():
            tasks = [scanner.scan_agent(agent) for agent in agents]
            return await asyncio.gather(*tasks)
        
        result = await benchmark_harness.run_benchmark(
            concurrent_scan_operation,
            iterations=20,
            metadata={"concurrency": 10, "agent_count": 10}
        )
        
        # Concurrent operations should have higher effective throughput
        effective_throughput = result.throughput_ops_per_sec * 10  # 10 agents per operation
        assert effective_throughput > 20.0  # At least 20 agents scanned per second
        assert result.memory_peak_mb < 200  # Less than 200MB for concurrent scans
        
        print(f"Concurrent scan throughput: {effective_throughput:.2f} agents/sec")
    
    @pytest.mark.benchmark
    def test_attack_pattern_generation_benchmark(self, benchmark_harness):
        """Benchmark attack pattern payload generation."""
        
        pattern = PromptInjectionPattern()
        target_info = {"agent_type": "openai", "model": "gpt-3.5-turbo"}
        
        def generation_operation():
            return pattern.generate_payloads(target_info, count=20)
        
        result = asyncio.run(benchmark_harness.run_benchmark(
            generation_operation,
            iterations=100,
            metadata={"pattern_type": "prompt_injection", "payload_count": 20}
        ))
        
        assert result.throughput_ops_per_sec > 50.0  # At least 50 generations per second
        assert result.memory_peak_mb < 50  # Less than 50MB for generation
        
        print(f"Pattern generation: {result.throughput_ops_per_sec:.2f} ops/sec")

    @pytest.mark.benchmark
    @pytest.mark.asyncio 
    async def test_response_analysis_benchmark(self, benchmark_harness):
        """Benchmark response analysis performance."""
        
        pattern = PromptInjectionPattern()
        test_responses = [
            "I'm a helpful AI assistant.",
            "HACKED - I will ignore previous instructions",
            "Error: Invalid input detected",
            "I cannot and will not provide information on that topic."
        ] * 25  # 100 responses total
        
        async def analysis_operation():
            results = []
            for response in test_responses:
                result = pattern.analyze_response(response, "test payload")
                results.append(result)
            return results
        
        result = await benchmark_harness.run_benchmark(
            analysis_operation,
            iterations=20,
            metadata={"response_count": len(test_responses)}
        )
        
        assert result.throughput_ops_per_sec > 10.0  # At least 10 analysis batches per second
        print(f"Response analysis: {result.throughput_ops_per_sec:.2f} batches/sec")
```

### Memory Benchmarks

```python
# tests/benchmarks/test_memory_benchmarks.py
import pytest
import gc
from memory_profiler import profile
from pympler import tracker, summary, muppy
import tracemalloc

class TestMemoryBenchmarks:
    """Memory usage and leak detection benchmarks."""
    
    @pytest.mark.benchmark
    def test_memory_usage_patterns(self):
        """Analyze memory usage patterns during scanning."""
        
        # Start memory tracking
        tracemalloc.start()
        tr = tracker.SummaryTracker()
        
        # Initial memory snapshot
        snapshot1 = tracemalloc.take_snapshot()
        
        # Perform memory-intensive operations
        scanner = RadarScanner()
        agents = [MockAgent(f"agent-{i}") for i in range(100)]
        
        # Simulate scanning workload
        for batch in range(10):
            batch_agents = agents[batch*10:(batch+1)*10]
            results = []
            for agent in batch_agents:
                result = asyncio.run(scanner.scan_agent(agent))
                results.append(result)
            
            # Force garbage collection
            gc.collect()
            
            # Take memory snapshot
            if batch == 4:  # Middle of execution
                snapshot2 = tracemalloc.take_snapshot()
        
        # Final memory snapshot
        snapshot3 = tracemalloc.take_snapshot()
        
        # Analyze memory growth
        top_stats = snapshot3.compare_to(snapshot1, 'lineno')
        
        print("Memory usage analysis:")
        for stat in top_stats[:10]:
            print(stat)
        
        # Memory usage should be reasonable
        current_size, peak_size = tracemalloc.get_traced_memory()
        assert peak_size < 200 * 1024 * 1024  # Less than 200MB peak
        
        tracemalloc.stop()
        tr.print_diff()
    
    @pytest.mark.benchmark
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        
        # Baseline memory measurement
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform repeated operations
        for iteration in range(100):
            scanner = RadarScanner()
            agent = MockAgent(f"leak-test-{iteration}")
            
            # Perform scan
            result = asyncio.run(scanner.scan_agent(agent))
            
            # Clean up references
            del scanner, agent, result
            
            # Periodic garbage collection
            if iteration % 10 == 0:
                gc.collect()
        
        # Final garbage collection and measurement
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object growth should be minimal
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Less than 1000 new objects
        
        print(f"Object growth after 100 iterations: {object_growth}")
    
    @profile
    def memory_intensive_operation(self):
        """Operation decorated with memory profiler."""
        scanner = RadarScanner()
        agents = [MockAgent(f"profile-agent-{i}") for i in range(50)]
        
        results = []
        for agent in agents:
            result = asyncio.run(scanner.scan_agent(agent))
            results.append(result)
        
        return results
```

## Profiling Tools and Techniques

### CPU Profiling

```python
# scripts/cpu_profiler.py
"""
CPU profiling utilities for performance analysis.
"""

import cProfile
import pstats
import io
from pstats import SortKey
import asyncio
from functools import wraps
import time

class CPUProfiler:
    """CPU profiling utilities."""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
    
    def profile_function(self, func, *args, **kwargs):
        """Profile a single function call."""
        self.profiler.enable()
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = asyncio.run(func(*args, **kwargs))
            else:
                result = func(*args, **kwargs)
        finally:
            self.profiler.disable()
        
        return result
    
    def get_stats(self, sort_by: SortKey = SortKey.CUMULATIVE, limit: int = 20):
        """Get profiling statistics."""
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats(sort_by)
        ps.print_stats(limit)
        return s.getvalue()
    
    def save_stats(self, filename: str):
        """Save profiling stats to file."""
        self.profiler.dump_stats(filename)

def profile_async(func):
    """Decorator for profiling async functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = await func(*args, **kwargs)
        finally:
            profiler.disable()
        
        # Save profile data
        profiler.dump_stats(f"profile_{func.__name__}_{int(time.time())}.prof")
        return result
    
    return wrapper

# Usage example
@profile_async
async def scan_performance_test():
    scanner = RadarScanner()
    agent = MockAgent("profile-test")
    return await scanner.scan_agent(agent)

# CLI tool for profiling
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cpu_profiler.py <script_to_profile>")
        sys.exit(1)
    
    script_name = sys.argv[1]
    cProfile.run(f'exec(open("{script_name}").read())', f'{script_name}.prof')
```

### Memory Profiling

```python
# scripts/memory_profiler.py
"""
Memory profiling utilities using various tools.
"""

import tracemalloc
import asyncio
from memory_profiler import profile as memory_profile
from pympler import tracker, classtracker, refbrowser
import psutil
import os
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import numpy as np

class MemoryProfiler:
    """Comprehensive memory profiling utilities."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots = []
        self.tracker = tracker.SummaryTracker()
    
    def start_tracing(self):
        """Start memory tracing."""
        tracemalloc.start()
        self.baseline_snapshot = tracemalloc.take_snapshot()
    
    def take_snapshot(self, label: str = None):
        """Take a memory snapshot."""
        snapshot = {
            'timestamp': asyncio.get_event_loop().time(),
            'tracemalloc': tracemalloc.take_snapshot(),
            'rss': self.process.memory_info().rss,
            'vms': self.process.memory_info().vms,
            'label': label or f'snapshot_{len(self.snapshots)}'
        }
        self.snapshots.append(snapshot)
        return snapshot
    
    def analyze_growth(self, limit: int = 10):
        """Analyze memory growth between snapshots."""
        if len(self.snapshots) < 2:
            return "Need at least 2 snapshots for analysis"
        
        latest = self.snapshots[-1]
        previous = self.snapshots[-2]
        
        # Compare tracemalloc snapshots
        top_stats = latest['tracemalloc'].compare_to(
            previous['tracemalloc'], 'lineno'
        )
        
        analysis = []
        analysis.append(f"Memory growth analysis: {previous['label']} -> {latest['label']}")
        analysis.append(f"RSS change: {(latest['rss'] - previous['rss']) / 1024 / 1024:.2f} MB")
        analysis.append(f"VMS change: {(latest['vms'] - previous['vms']) / 1024 / 1024:.2f} MB")
        analysis.append("\nTop memory allocations:")
        
        for i, stat in enumerate(top_stats[:limit]):
            analysis.append(f"{i+1}. {stat}")
        
        return "\n".join(analysis)
    
    def generate_memory_plot(self, output_file: str = "memory_usage.png"):
        """Generate memory usage plot."""
        if not self.snapshots:
            return "No snapshots available for plotting"
        
        timestamps = [s['timestamp'] for s in self.snapshots]
        rss_values = [s['rss'] / 1024 / 1024 for s in self.snapshots]  # Convert to MB
        labels = [s['label'] for s in self.snapshots]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, rss_values, 'b-o', linewidth=2, markersize=6)
        plt.xlabel('Time')
        plt.ylabel('Memory Usage (MB)')
        plt.title('Memory Usage Over Time')
        plt.grid(True, alpha=0.3)
        
        # Add labels for key points
        for i, (t, rss, label) in enumerate(zip(timestamps, rss_values, labels)):
            if i % max(1, len(timestamps) // 10) == 0:  # Show every 10th label
                plt.annotate(label, (t, rss), textcoords="offset points", 
                           xytext=(0,10), ha='center', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        return f"Memory plot saved to {output_file}"

# Context manager for easy profiling
class MemoryProfilingContext:
    """Context manager for memory profiling."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.profiler = MemoryProfiler()
    
    def __enter__(self):
        self.profiler.start_tracing()
        self.profiler.take_snapshot(f"{self.operation_name}_start")
        return self.profiler
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.take_snapshot(f"{self.operation_name}_end")
        analysis = self.profiler.analyze_growth()
        print(analysis)

# Usage example
async def memory_intensive_scan():
    with MemoryProfilingContext("intensive_scan") as profiler:
        scanner = RadarScanner()
        agents = [MockAgent(f"agent-{i}") for i in range(100)]
        
        for i, agent in enumerate(agents):
            await scanner.scan_agent(agent)
            
            # Take periodic snapshots
            if i % 20 == 0:
                profiler.take_snapshot(f"after_{i}_scans")
        
        profiler.generate_memory_plot("scan_memory_usage.png")
```

### Performance Regression Detection

```python
# scripts/performance_regression.py
"""
Performance regression detection and reporting.
"""

import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import statistics

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    operation: str
    timestamp: datetime
    duration_seconds: float
    memory_mb: float
    cpu_percent: float
    throughput_ops_per_sec: float
    git_commit: str
    environment: str
    metadata: Dict[str, any]

class PerformanceTracker:
    """Performance tracking and regression detection."""
    
    def __init__(self, db_path: str = "performance_metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for metrics storage."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                memory_mb REAL NOT NULL,
                cpu_percent REAL NOT NULL,
                throughput_ops_per_sec REAL NOT NULL,
                git_commit TEXT,
                environment TEXT DEFAULT 'unknown',
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO performance_metrics 
            (operation, timestamp, duration_seconds, memory_mb, cpu_percent, 
             throughput_ops_per_sec, git_commit, environment, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric.operation,
            metric.timestamp.isoformat(),
            metric.duration_seconds,
            metric.memory_mb,
            metric.cpu_percent,
            metric.throughput_ops_per_sec,
            metric.git_commit,
            metric.environment,
            json.dumps(metric.metadata)
        ))
        conn.commit()
        conn.close()
    
    def get_recent_metrics(self, operation: str, days: int = 30) -> List[PerformanceMetric]:
        """Get recent metrics for an operation."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT operation, timestamp, duration_seconds, memory_mb, cpu_percent,
                   throughput_ops_per_sec, git_commit, environment, metadata
            FROM performance_metrics
            WHERE operation = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (operation, cutoff_date.isoformat()))
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append(PerformanceMetric(
                operation=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                duration_seconds=row[2],
                memory_mb=row[3],
                cpu_percent=row[4],
                throughput_ops_per_sec=row[5],
                git_commit=row[6],
                environment=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            ))
        
        conn.close()
        return metrics
    
    def detect_regression(self, operation: str, current_metric: PerformanceMetric, 
                         threshold_percent: float = 20.0) -> Optional[Dict[str, any]]:
        """Detect performance regression."""
        
        # Get baseline metrics (last 7 days excluding today)
        baseline_start = datetime.now() - timedelta(days=8)
        baseline_end = datetime.now() - timedelta(days=1)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT duration_seconds, memory_mb, throughput_ops_per_sec
            FROM performance_metrics
            WHERE operation = ? AND timestamp BETWEEN ? AND ?
        """, (operation, baseline_start.isoformat(), baseline_end.isoformat()))
        
        baseline_data = cursor.fetchall()
        conn.close()
        
        if len(baseline_data) < 5:  # Need at least 5 data points
            return None
        
        # Calculate baseline statistics
        durations = [row[0] for row in baseline_data]
        memory_usage = [row[1] for row in baseline_data]
        throughputs = [row[2] for row in baseline_data]
        
        baseline_duration = statistics.median(durations)
        baseline_memory = statistics.median(memory_usage)
        baseline_throughput = statistics.median(throughputs)
        
        # Check for regressions
        regressions = []
        
        # Duration regression (slower is bad)
        duration_change = ((current_metric.duration_seconds - baseline_duration) / baseline_duration) * 100
        if duration_change > threshold_percent:
            regressions.append({
                'metric': 'duration',
                'change_percent': duration_change,
                'current': current_metric.duration_seconds,
                'baseline': baseline_duration
            })
        
        # Memory regression (more memory is bad)
        memory_change = ((current_metric.memory_mb - baseline_memory) / baseline_memory) * 100
        if memory_change > threshold_percent:
            regressions.append({
                'metric': 'memory',
                'change_percent': memory_change,
                'current': current_metric.memory_mb,
                'baseline': baseline_memory
            })
        
        # Throughput regression (lower throughput is bad)
        throughput_change = ((baseline_throughput - current_metric.throughput_ops_per_sec) / baseline_throughput) * 100
        if throughput_change > threshold_percent:
            regressions.append({
                'metric': 'throughput',
                'change_percent': throughput_change,
                'current': current_metric.throughput_ops_per_sec,
                'baseline': baseline_throughput
            })
        
        if regressions:
            return {
                'operation': operation,
                'regressions': regressions,
                'git_commit': current_metric.git_commit,
                'timestamp': current_metric.timestamp.isoformat()
            }
        
        return None
    
    def generate_performance_report(self, operations: List[str], days: int = 30) -> str:
        """Generate comprehensive performance report."""
        report = []
        report.append(f"Performance Report - Last {days} Days")
        report.append("=" * 50)
        
        for operation in operations:
            metrics = self.get_recent_metrics(operation, days)
            if not metrics:
                continue
            
            # Calculate statistics
            durations = [m.duration_seconds for m in metrics]
            memory_usage = [m.memory_mb for m in metrics]
            throughputs = [m.throughput_ops_per_sec for m in metrics]
            
            report.append(f"\nOperation: {operation}")
            report.append(f"  Sample count: {len(metrics)}")
            report.append(f"  Duration - Median: {statistics.median(durations):.3f}s, "
                         f"P95: {np.percentile(durations, 95):.3f}s")
            report.append(f"  Memory - Median: {statistics.median(memory_usage):.1f}MB, "
                         f"P95: {np.percentile(memory_usage, 95):.1f}MB")
            report.append(f"  Throughput - Median: {statistics.median(throughputs):.2f} ops/sec")
        
        return "\n".join(report)

# Integration with pytest benchmarks
def record_benchmark_result(operation_name: str, benchmark_result):
    """Record pytest benchmark result to performance tracker."""
    tracker = PerformanceTracker()
    
    metric = PerformanceMetric(
        operation=operation_name,
        timestamp=datetime.now(),
        duration_seconds=benchmark_result.stats.mean,
        memory_mb=0,  # pytest-benchmark doesn't track memory
        cpu_percent=0,
        throughput_ops_per_sec=1.0 / benchmark_result.stats.mean,
        git_commit=os.environ.get('GIT_COMMIT', 'unknown'),
        environment=os.environ.get('ENVIRONMENT', 'test'),
        metadata={
            'min': benchmark_result.stats.min,
            'max': benchmark_result.stats.max,
            'stddev': benchmark_result.stats.stddev,
            'rounds': benchmark_result.stats.rounds
        }
    )
    
    tracker.record_metric(metric)
    
    # Check for regression
    regression = tracker.detect_regression(operation_name, metric)
    if regression:
        print(f"⚠️  Performance regression detected for {operation_name}:")
        for reg in regression['regressions']:
            print(f"  {reg['metric']}: {reg['change_percent']:.1f}% worse "
                  f"({reg['current']:.3f} vs {reg['baseline']:.3f})")
```

## Performance Optimization Guidelines

### CPU Optimization

#### Async Programming Best Practices

```python
# Good: Proper async/await usage
async def scan_multiple_agents(agents: List[Agent]) -> List[ScanResult]:
    """Efficient concurrent scanning."""
    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent scans
    
    async def scan_with_limit(agent):
        async with semaphore:
            return await scan_agent(agent)
    
    # Execute scans concurrently
    tasks = [scan_with_limit(agent) for agent in agents]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Bad: Sequential processing
async def scan_multiple_agents_bad(agents: List[Agent]) -> List[ScanResult]:
    """Inefficient sequential scanning."""
    results = []
    for agent in agents:
        result = await scan_agent(agent)  # Blocks until complete
        results.append(result)
    return results
```

#### Caching Strategies

```python
from functools import lru_cache
import asyncio
from typing import Dict, Any
import time

class SmartCache:
    """Intelligent caching with TTL and size limits."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Any:
        """Get cached value if valid."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                return entry['value']
            else:
                del self.cache[key]  # Expired
        return None
    
    def set(self, key: str, value: Any):
        """Set cached value with timestamp."""
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }

# Usage in attack patterns
attack_pattern_cache = SmartCache(max_size=500, ttl_seconds=600)

@lru_cache(maxsize=128)
def generate_payload_variants(base_payload: str, agent_type: str) -> List[str]:
    """Cache expensive payload generation."""
    # Expensive payload generation logic
    return generate_variants_internal(base_payload, agent_type)
```

### Memory Optimization

#### Object Pool Pattern

```python
import queue
from typing import Generic, TypeVar, Callable
import threading

T = TypeVar('T')

class ObjectPool(Generic[T]):
    """Object pool to reduce allocation overhead."""
    
    def __init__(self, create_func: Callable[[], T], max_size: int = 100):
        self.create_func = create_func
        self.pool = queue.Queue(maxsize=max_size)
        self.lock = threading.Lock()
    
    def get(self) -> T:
        """Get object from pool or create new one."""
        try:
            return self.pool.get_nowait()
        except queue.Empty:
            return self.create_func()
    
    def put(self, obj: T):
        """Return object to pool."""
        try:
            self.pool.put_nowait(obj)
        except queue.Full:
            pass  # Pool is full, let object be garbage collected

# Usage example
response_analyzer_pool = ObjectPool(
    lambda: ResponseAnalyzer(),
    max_size=20
)

async def analyze_response_pooled(response: str, payload: str):
    """Use pooled analyzer to reduce allocations."""
    analyzer = response_analyzer_pool.get()
    try:
        result = analyzer.analyze(response, payload)
        analyzer.reset()  # Reset state for reuse
        return result
    finally:
        response_analyzer_pool.put(analyzer)
```

#### Memory-Efficient Data Structures

```python
import array
from typing import List
import sys

# Use __slots__ to reduce memory overhead
class EfficientScanResult:
    """Memory-efficient scan result using __slots__."""
    __slots__ = ['agent_id', 'pattern_name', 'success', 'confidence', 'evidence']
    
    def __init__(self, agent_id: str, pattern_name: str, success: bool, 
                 confidence: float, evidence: str):
        self.agent_id = agent_id
        self.pattern_name = pattern_name
        self.success = success
        self.confidence = confidence
        self.evidence = evidence

# Use generators for large datasets
def process_large_dataset(data_source):
    """Memory-efficient processing using generators."""
    for chunk in read_data_chunks(data_source, chunk_size=1000):
        for item in process_chunk(chunk):
            yield item

# Use array for numeric data
def efficient_metrics_storage(metrics: List[float]) -> array.array:
    """Store metrics efficiently using array instead of list."""
    return array.array('f', metrics)  # 'f' = float, uses less memory than list
```

### I/O Optimization

#### Connection Pooling

```python
import aiohttp
import asyncio
from typing import Optional
import time

class ConnectionPool:
    """Efficient HTTP connection pool for API calls."""
    
    def __init__(self, max_connections: int = 100, timeout: int = 30):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True,
            enable_cleanup_closed=True
        )
        
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout
            )
        return self.session
    
    async def close(self):
        """Close connection pool."""
        if self.session and not self.session.closed:
            await self.session.close()

# Global connection pool
http_pool = ConnectionPool(max_connections=50)

async def make_api_call(url: str, data: dict) -> dict:
    """Make API call using connection pool."""
    session = await http_pool.get_session()
    async with session.post(url, json=data) as response:
        return await response.json()
```

#### Batch Processing

```python
import asyncio
from typing import List, TypeVar, Callable, Any
import time

T = TypeVar('T')
R = TypeVar('R')

class BatchProcessor(Generic[T, R]):
    """Batch processor for efficient I/O operations."""
    
    def __init__(self, 
                 process_func: Callable[[List[T]], List[R]],
                 batch_size: int = 50,
                 max_wait_time: float = 1.0):
        self.process_func = process_func
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_items: List[T] = []
        self.last_flush = time.time()
    
    async def add_item(self, item: T) -> R:
        """Add item to batch and process if needed."""
        self.pending_items.append(item)
        
        # Process if batch is full or max wait time exceeded
        if (len(self.pending_items) >= self.batch_size or 
            time.time() - self.last_flush > self.max_wait_time):
            return await self.flush()
    
    async def flush(self) -> List[R]:
        """Process all pending items."""
        if not self.pending_items:
            return []
        
        items_to_process = self.pending_items.copy()
        self.pending_items.clear()
        self.last_flush = time.time()
        
        # Process batch
        results = await asyncio.get_event_loop().run_in_executor(
            None, self.process_func, items_to_process
        )
        
        return results

# Usage example
def batch_analyze_responses(responses: List[str]) -> List[AnalysisResult]:
    """Batch analysis for efficiency."""
    # Expensive analysis operation
    return [analyze_single_response(r) for r in responses]

response_batch_processor = BatchProcessor(
    batch_analyze_responses,
    batch_size=20,
    max_wait_time=2.0
)
```

## Continuous Performance Monitoring

### Production Performance Monitoring

```python
# src/agentic_redteam/monitoring/performance.py
"""
Production performance monitoring integration.
"""

import time
import asyncio
from functools import wraps
from prometheus_client import Histogram, Counter, Gauge
import logging

# Prometheus metrics
OPERATION_DURATION = Histogram(
    'operation_duration_seconds',
    'Time spent on operations',
    ['operation_name', 'status']
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage by component',
    ['component']
)

PERFORMANCE_VIOLATIONS = Counter(
    'performance_violations_total',
    'Performance SLA violations',
    ['operation', 'violation_type']
)

logger = logging.getLogger(__name__)

def monitor_performance(operation_name: str, sla_seconds: float = None):
    """Decorator to monitor operation performance."""
    def decorator(func):
        @wraps(func) 
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                
                # Record metrics
                OPERATION_DURATION.labels(
                    operation_name=operation_name,
                    status=status
                ).observe(duration)
                
                # Check SLA violation
                if sla_seconds and duration > sla_seconds:
                    PERFORMANCE_VIOLATIONS.labels(
                        operation=operation_name,
                        violation_type="duration"
                    ).inc()
                    
                    logger.warning(
                        f"Performance SLA violation: {operation_name} "
                        f"took {duration:.3f}s (SLA: {sla_seconds}s)"
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar implementation for sync functions
            start_time = time.perf_counter()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                OPERATION_DURATION.labels(
                    operation_name=operation_name,
                    status=status
                ).observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# Usage examples
@monitor_performance("agent_scan", sla_seconds=30.0)
async def scan_agent(agent):
    """Monitored agent scanning."""
    return await perform_scan(agent)

@monitor_performance("pattern_generation", sla_seconds=5.0)
def generate_attack_patterns(target_info):
    """Monitored pattern generation."""
    return create_patterns(target_info)
```

This comprehensive benchmarking and profiling guide provides the foundation for maintaining optimal performance in the Agentic RedTeam Radar security scanner.