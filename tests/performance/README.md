# Performance Testing Suite

This directory contains comprehensive performance tests, benchmarks, and load testing utilities for the Agentic RedTeam Radar security scanner.

## Overview

The performance testing suite is designed to:
- Monitor system resource usage during security scans
- Benchmark core components under various loads
- Identify performance bottlenecks and memory leaks
- Validate performance requirements and SLAs
- Provide regression testing for performance characteristics

## Test Categories

### 1. Scanner Performance Tests (`test_scanner_performance.py`)
- **Single Agent Scanning**: Tests performance of scanning individual agents
- **Batch Agent Scanning**: Tests performance with multiple agents simultaneously 
- **Concurrent Scanning**: Tests parallel scanning capabilities
- **Memory Usage Under Load**: Monitors memory consumption during sustained operations
- **Load Testing**: Validates performance under high request volumes

### 2. Attack Pattern Performance Tests (`test_attack_patterns_performance.py`)
- **Payload Generation**: Benchmarks attack payload creation speed
- **Response Evaluation**: Tests analysis performance for various response types
- **Pattern Complexity Scaling**: Validates performance across different complexity levels
- **Memory Efficiency**: Monitors memory usage patterns
- **CPU Utilization**: Tests CPU efficiency during intensive operations

## Running Performance Tests

### Basic Execution
```bash
# Run all performance tests
pytest tests/performance/ -m performance -v

# Run only benchmark tests
pytest tests/performance/ -m benchmark -v

# Run load tests
pytest tests/performance/ -m load_test -v

# Run memory-intensive tests
pytest tests/performance/ -m memory_intensive -v

# Run CPU-intensive tests
pytest tests/performance/ -m cpu_intensive -v
```

### Configuration via Environment Variables

```bash
# Performance test configuration
export PERF_ITERATIONS=1000        # Number of benchmark iterations
export PERF_WARMUP=50             # Warmup iterations before measurement
export PERF_TIMEOUT=120.0         # Timeout for individual tests (seconds)
export PERF_WORKERS=8             # Number of parallel workers

# Load test configuration
export LOAD_CONCURRENT=20         # Concurrent requests
export LOAD_TOTAL=5000           # Total requests for load test
export LOAD_RAMPUP=30.0          # Ramp-up time (seconds)
export LOAD_DURATION=300.0       # Load test duration (seconds)
```

### Advanced Execution Options

```bash
# Run with detailed memory profiling
pytest tests/performance/ -m performance --tb=short -s

# Generate performance report
pytest tests/performance/ -m performance --json-report --json-report-file=perf_report.json

# Run specific performance test categories
pytest tests/performance/test_scanner_performance.py::TestScannerPerformance::test_single_agent_scan_performance -v

# Run with custom thresholds (modify conftest.py accordingly)
pytest tests/performance/ -m performance --maxfail=1
```

## Performance Thresholds

The following performance thresholds are defined and monitored:

| Operation | Threshold | Description |
|-----------|-----------|-------------|
| Single Agent Scan | < 5.0s | Maximum time for scanning one agent |
| Batch Agent Scan | < 30.0s | Maximum time for batch scanning |
| Attack Generation | < 1.0s | Maximum time for generating attack payloads |
| Response Analysis | < 2.0s | Maximum time for analyzing responses |
| Memory Usage | < 100MB | Maximum memory usage during operations |
| CPU Usage | < 80% | Maximum CPU utilization |

## Monitoring and Reporting

### Performance Reports
After running performance tests, reports are generated:
- `performance_report.json`: Detailed metrics from all test runs
- Console output with key performance indicators
- Memory usage patterns and potential leaks
- CPU utilization statistics

### Key Metrics Tracked
- **Execution Time**: Time taken for various operations
- **Memory Delta**: Memory usage changes during test execution
- **Peak Memory**: Maximum memory consumption
- **CPU Percentage**: CPU utilization during tests
- **Thread Count**: Number of active threads
- **Throughput**: Operations per second for various components

## Test Fixtures and Utilities

### PerformanceMonitor
- Monitors system resources during test execution
- Tracks memory usage, CPU utilization, and execution time
- Provides detailed metrics for analysis

### Mock Components
- **MockAgent**: Simulates AI agents with configurable response times
- **MockRadarScanner**: Simulates scanner operations for isolated testing
- **MockAttackPattern**: Provides controllable attack pattern behavior

### Configuration Fixtures
- **performance_thresholds**: Defines acceptable performance limits
- **benchmark_config**: Configuration for benchmark tests
- **load_test_config**: Configuration for load testing scenarios

## Performance Optimization Guidelines

### Code Optimization
1. **Minimize Memory Allocations**: Reuse objects where possible
2. **Optimize Loops**: Use list comprehensions and vectorized operations
3. **Profile Regularly**: Use built-in profiling tools to identify bottlenecks
4. **Cache Results**: Implement caching for expensive operations

### System Optimization  
1. **Async Operations**: Use asyncio for I/O-bound operations
2. **Parallel Processing**: Leverage multi-threading for CPU-bound tasks
3. **Resource Pooling**: Pool connections and expensive resources
4. **Lazy Loading**: Load resources only when needed

### Monitoring Best Practices
1. **Baseline Establishment**: Record performance baselines for comparison
2. **Regression Testing**: Run performance tests in CI/CD pipeline
3. **Alert Thresholds**: Set up alerts for performance degradation
4. **Regular Profiling**: Profile application under realistic loads

## Integration with CI/CD

### GitHub Actions Integration
```yaml
name: Performance Tests
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .[dev]
          pip install pytest-benchmark pytest-xdist
      - name: Run performance tests
        run: |
          pytest tests/performance/ -m "performance and not load_test" --benchmark-json=benchmark.json
      - name: Upload performance results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: |
            performance_report.json
            benchmark.json
```

### Performance Regression Detection
- Compare current performance against baseline
- Fail builds if performance degrades beyond thresholds
- Generate alerts for significant performance changes

## Troubleshooting

### Common Issues
1. **High Memory Usage**: Check for memory leaks in mock objects
2. **Slow Test Execution**: Reduce iteration counts for CI environments
3. **Inconsistent Results**: Ensure system is not under load during testing
4. **Timeout Errors**: Increase timeout values for slower systems

### Debugging Tips
1. **Verbose Logging**: Use `-s` flag to see print statements
2. **Profiling**: Use `cProfile` or `py-spy` for detailed profiling
3. **Memory Analysis**: Use `memory_profiler` for memory debugging
4. **System Monitoring**: Use `htop` or similar tools during test execution

## Contributing

When adding new performance tests:
1. Follow the existing test structure and naming conventions
2. Use appropriate markers (`@pytest.mark.performance`, etc.)
3. Include performance thresholds and validation
4. Document expected behavior and resource usage
5. Consider both positive and negative test scenarios

## Future Enhancements

- Integration with continuous performance monitoring tools
- Automated performance regression detection
- Performance comparison across different environments
- GPU performance testing for ML-accelerated components
- Distributed load testing capabilities