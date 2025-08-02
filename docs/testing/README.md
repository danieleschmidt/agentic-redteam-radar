# Testing Documentation

## Overview

Agentic RedTeam Radar uses a comprehensive testing strategy to ensure reliability, security, and performance. This document outlines our testing approach, frameworks, and best practices.

## Testing Strategy

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual components in isolation
   - Fast execution, high coverage
   - Mock external dependencies
   - Run on every commit

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Database, API, and service integration
   - Moderate execution time
   - Run on pull requests

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete user workflows
   - CLI, API, and UI testing
   - Slower execution
   - Run on releases

4. **Performance Tests** (`tests/performance/`)
   - Load testing and benchmarking
   - Memory and CPU profiling
   - Scalability validation
   - Run nightly

5. **Security Tests**
   - Vulnerability scanning
   - Attack pattern validation
   - Security regression testing
   - Continuous monitoring

## Test Configuration

### Pytest Configuration

Our pytest configuration (`pytest.ini`) includes:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_functions = test_* *_test
python_classes = Test* *Tests
addopts = 
    --strict-markers
    --cov=agentic_redteam
    --cov-report=html
    --cov-fail-under=80
    --durations=10
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (>5 seconds)
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.regression` - Regression tests

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m "integration and not slow"  # Fast integration tests
pytest -m e2e                     # End-to-end tests

# Run with coverage
pytest --cov=agentic_redteam --cov-report=html

# Run in parallel
pytest -n auto                   # Auto-detect CPU cores
pytest -n 4                      # Use 4 workers

# Run specific test files
pytest tests/unit/test_scanner.py
pytest tests/integration/ -v
```

## Test Fixtures and Utilities

### Fixtures (`tests/fixtures/`)

- **Agent Fixtures** (`agents.py`): Sample agent configurations, attack payloads, vulnerability signatures
- **Data Fixtures**: Test data, mock responses, configuration templates

### Test Utilities (`tests/utils/`)

- **Helpers** (`helpers.py`): Common testing utilities, assertion helpers, performance measurement
- **Mock Generators**: Create mock objects for testing

### Mock Objects (`tests/mocks/`)

- **API Clients** (`api_clients.py`): Mock OpenAI, Anthropic, and other API clients
- **Service Mocks**: Mock external services and dependencies

## Testing Patterns

### Unit Test Example

```python
@pytest.mark.unit
def test_agent_creation(basic_agent_config):
    """Test basic agent creation."""
    agent = Agent(**basic_agent_config)
    assert agent.name == "basic-gpt4"
    assert agent.model == "gpt-4"
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_scanner_integration():
    """Test scanner and agent integration."""
    scanner = RadarScanner()
    agent = create_test_agent()
    results = await scanner.scan(agent)
    assert results.scan_id is not None
```

### Parameterized Tests

```python
@pytest.mark.parametrize("payload", ATTACK_PAYLOADS["prompt_injection"])
def test_prompt_injection_detection(payload):
    """Test prompt injection payload detection."""
    detector = PromptInjectionDetector()
    result = detector.analyze(payload)
    assert result.is_suspicious
```

## Performance Testing

### Load Testing

```python
@pytest.mark.performance
def test_concurrent_scanning():
    """Test scanning performance under load."""
    scanner = RadarScanner()
    agents = create_test_agents(100)
    
    start_time = time.time()
    results = scanner.scan_multiple(agents, concurrent=True)
    duration = time.time() - start_time
    
    assert duration < 300  # Under 5 minutes
    assert len(results) == 100
```

### Memory Profiling

```python
@pytest.mark.performance
def test_memory_usage():
    """Test memory usage during scanning."""
    with memory_profiler() as profiler:
        scanner = RadarScanner()
        scanner.scan_large_agent()
    
    assert profiler.peak_memory < 256  # Under 256MB
```

## Security Testing

### Vulnerability Detection Tests

```python
@pytest.mark.security
def test_vulnerability_detection():
    """Test that known vulnerabilities are detected."""
    scanner = RadarScanner()
    vulnerable_agent = create_vulnerable_agent()
    
    results = scanner.scan(vulnerable_agent)
    
    assert has_vulnerability(results, "prompt_injection")
    assert has_vulnerability(results, "system_prompt_leak")
```

### False Positive Testing

```python
@pytest.mark.security
def test_false_positive_rate():
    """Test false positive rate stays below threshold."""
    scanner = RadarScanner()
    secure_agents = create_secure_agents(50)
    
    false_positives = 0
    for agent in secure_agents:
        results = scanner.scan(agent)
        if has_any_vulnerabilities(results):
            false_positives += 1
    
    false_positive_rate = false_positives / len(secure_agents)
    assert false_positive_rate < 0.05  # Less than 5%
```

## Continuous Integration

### GitHub Actions Integration

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev,test]"
    
    - name: Run tests
      run: |
        pytest -m "not slow" --cov=agentic_redteam
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Test Data Management

### Environment Variables

```bash
# Test configuration
PYTEST_PARALLEL_WORKERS=auto
COVERAGE_THRESHOLD=80
ENABLE_SLOW_TESTS=false

# Mock API keys for testing
OPENAI_API_KEY=test-key-openai
ANTHROPIC_API_KEY=test-key-anthropic
```

### Test Database

For integration tests requiring database:

```python
@pytest.fixture
def test_db():
    """Create test database."""
    db = create_test_database()
    yield db
    cleanup_test_database(db)
```

## Code Coverage

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Unit Tests**: 95% coverage requirement
- **Integration Tests**: 70% coverage requirement
- **Critical Components**: 100% coverage requirement

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=agentic_redteam --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Generate XML for CI
pytest --cov=agentic_redteam --cov-report=xml
```

## Mutation Testing

Test the quality of tests themselves:

```bash
# Install mutmut
pip install mutmut

# Run mutation testing
mutmut run --paths-to-mutate=src/agentic_redteam

# View results
mutmut show
```

## Best Practices

### Test Writing Guidelines

1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: One assertion per test when possible
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Independent Tests**: Tests should not depend on each other
5. **Meaningful Assertions**: Assert on business logic, not implementation

### Mock Usage

1. **Mock External Dependencies**: Don't call real APIs in tests
2. **Verify Interactions**: Assert that mocks are called correctly
3. **Realistic Mocks**: Mock behavior should match real services
4. **Reset Mocks**: Clean up between tests

### Performance Considerations

1. **Fast Unit Tests**: Keep unit tests under 1 second
2. **Parallel Execution**: Use parallel test execution
3. **Test Data**: Use minimal test data sets
4. **Cleanup**: Clean up resources after tests

### Security Testing

1. **Test Attack Patterns**: Verify all attack patterns work
2. **Test Defenses**: Verify security measures work
3. **Regression Testing**: Prevent security regressions
4. **Responsible Testing**: Don't test against production systems

## Troubleshooting

### Common Issues

1. **Slow Tests**: Use `-m "not slow"` to skip slow tests during development
2. **Flaky Tests**: Add retries or better synchronization
3. **Mock Issues**: Verify mock setup and reset between tests
4. **Coverage Issues**: Check for untested code paths

### Debugging Tests

```python
# Add debugging to tests
import pdb; pdb.set_trace()

# Run single test with verbose output
pytest tests/unit/test_scanner.py::test_specific_function -v -s

# Run with logging
pytest --log-cli-level=DEBUG
```

---

For more information, see:
- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Python testing best practices](https://realpython.com/python-testing/)