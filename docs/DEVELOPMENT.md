# Development Guide

## Quick Start

### Prerequisites
- Python 3.10+
- Git
- Virtual environment tool (venv/conda)

### Setup
```bash
# Clone repository
git clone https://github.com/terragonlabs/agentic-redteam-radar.git
cd agentic-redteam-radar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install
```

### Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Required API keys for testing
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=agentic_redteam

# Specific test file
pytest tests/test_scanner.py

# Parallel execution
pytest -n auto
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint
flake8
mypy src/

# All quality checks
pre-commit run --all-files
```

## Project Structure

```
src/agentic_redteam/
├── __init__.py
├── scanner.py          # Main scanner interface
├── agent.py           # Agent abstraction
├── attacks/           # Attack pattern implementations
├── models/            # Data models and schemas
├── utils/             # Utility functions
└── cli.py            # Command line interface

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── fixtures/         # Test data and mocks

docs/
├── api/              # API documentation
├── guides/           # User guides
└── examples/         # Code examples
```

## Architecture

### Core Components
- **Scanner**: Orchestrates security testing
- **Agent**: Abstracts different AI agent implementations
- **Attack Patterns**: Modular vulnerability tests
- **Reporting**: Results analysis and visualization

### Extension Points
- Custom attack patterns
- Agent framework adapters
- Report generators
- CLI commands

## Testing Strategy

### Test Types
- **Unit**: Individual component testing
- **Integration**: Multi-component interactions
- **Security**: Attack pattern validation
- **Performance**: Scalability testing

### Mock Strategy
- External API calls mocked in tests
- Test fixtures for different agent types
- Reproducible attack scenarios

## Release Process

### Version Management
- Semantic versioning (MAJOR.MINOR.PATCH)
- Version in `src/agentic_redteam/__init__.py`
- Git tags for releases

### Deployment
- PyPI package distribution
- Docker image updates
- Documentation site deployment

## Debugging

### Common Issues
- API rate limiting: Use test API keys
- Import errors: Check PYTHONPATH
- Test failures: Verify environment setup

### Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Profiling
```bash
# Performance profiling
python -m cProfile -s tottime script.py

# Memory profiling
pip install memory-profiler
python -m memory_profiler script.py
```