# CI/CD Setup Guide

## Overview

This document provides templates and guidance for setting up CI/CD workflows for the Agentic RedTeam Radar project.

**Note**: Due to security restrictions, actual GitHub Actions YAML files are not included. Use these templates to create your workflows manually.

## Required Workflows

### 1. Test Workflow (.github/workflows/test.yml)

**Purpose**: Run tests on every push and pull request

**Triggers**: 
- Push to main branch
- Pull requests to main branch
- Manual dispatch

**Template Structure**:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest --cov=agentic_redteam --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 2. Security Workflow (.github/workflows/security.yml)

**Purpose**: Security scanning and vulnerability detection

**Template Structure**:
```yaml
name: Security
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install bandit[toml] pip-audit
      - name: Run Bandit
        run: bandit -r src/
      - name: Run pip-audit
        run: pip-audit
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
```

### 3. Code Quality Workflow (.github/workflows/quality.yml)

**Purpose**: Code formatting, linting, and type checking

**Template Structure**:
```yaml
name: Code Quality
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install black isort flake8 mypy
      - name: Check formatting
        run: |
          black --check .
          isort --check-only .
      - name: Lint
        run: flake8
      - name: Type check
        run: mypy src/
```

### 4. Release Workflow (.github/workflows/release.yml)

**Purpose**: Automated package building and publishing

**Template Structure**:
```yaml
name: Release
on:
  release:
    types: [published]
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Build package
        run: |
          pip install build
          python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

## Environment Setup

### Required Secrets

Add these secrets in repository settings:

1. **PYPI_API_TOKEN**: For package publishing
2. **CODECOV_TOKEN**: For coverage reporting
3. **OPENAI_API_KEY**: For integration tests (optional)
4. **ANTHROPIC_API_KEY**: For integration tests (optional)

### Environment Variables

Configure in workflow files:

```yaml
env:
  PYTHONPATH: src/
  PYTEST_ARGS: --strict-markers --strict-config
```

## Branch Protection Rules

Recommended settings for main branch:

- **Require pull request reviews**: 1 required reviewer
- **Require status checks**: All CI workflows must pass
- **Require branches to be up to date**: Yes
- **Restrict pushes**: Only allow specific roles
- **Allow force pushes**: No
- **Allow deletions**: No

## Workflow Dependencies

### External Actions Used
- `actions/checkout@v4`: Repository checkout
- `actions/setup-python@v4`: Python environment setup
- `codecov/codecov-action@v3`: Coverage reporting
- `github/codeql-action@v2`: Security scanning
- `pypa/gh-action-pypi-publish@release/v1`: Package publishing

### Security Considerations
- Pin action versions for security
- Use dependabot for action updates
- Minimize secret exposure
- Use GITHUB_TOKEN when possible

## Performance Optimization

### Caching Strategy
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.txt') }}
    restore-keys: pip-
```

### Matrix Strategy
- Test against multiple Python versions
- Parallel job execution
- Fail-fast disabled for comprehensive testing

## Monitoring and Alerts

### Status Badges
Add to README.md:
```markdown
[![Tests](https://github.com/user/repo/workflows/Tests/badge.svg)](https://github.com/user/repo/actions)
[![Security](https://github.com/user/repo/workflows/Security/badge.svg)](https://github.com/user/repo/actions)
[![codecov](https://codecov.io/gh/user/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/user/repo)
```

### Notification Setup
- Email notifications for failed workflows
- Slack integration for deployment notifications
- GitHub Issues creation for security findings

## Manual Setup Instructions

1. **Create Workflow Directory**:
   ```bash
   mkdir -p .github/workflows
   ```

2. **Create Workflow Files**:
   Use templates above to create YAML files

3. **Configure Repository Settings**:
   - Add required secrets
   - Set up branch protection
   - Enable security features

4. **Test Workflows**:
   - Create test PR to verify functionality
   - Check workflow logs for issues
   - Validate security scans

## Troubleshooting

### Common Issues
- **Permission denied**: Check repository secrets and permissions
- **Import errors**: Verify PYTHONPATH configuration
- **Test failures**: Ensure all dependencies are installed
- **Security alerts**: Review and address flagged vulnerabilities

### Debugging Steps
1. Check workflow logs in Actions tab
2. Verify environment variable configuration
3. Test commands locally before pushing
4. Review security scan results carefully

## Future Enhancements

### Planned Additions
- Automated dependency updates (Dependabot)
- Performance benchmarking workflows
- Multi-environment testing
- Container security scanning
- SLSA compliance documentation

### Integration Opportunities
- SonarQube for code quality analysis
- Snyk for advanced vulnerability scanning
- Docker Hub for container publishing
- Documentation site deployment