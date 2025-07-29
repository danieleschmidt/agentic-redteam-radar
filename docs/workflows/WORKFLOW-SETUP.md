# GitHub Actions Workflow Setup

This directory contains template GitHub Actions workflows that need to be manually added to your repository due to GitHub App permission restrictions.

## 🚀 Quick Setup

To enable the complete CI/CD pipeline, copy these files to `.github/workflows/`:

```bash
# Create the workflows directory
mkdir -p .github/workflows

# Copy the workflow templates
cp docs/workflows/templates/ci.yml .github/workflows/
cp docs/workflows/templates/security.yml .github/workflows/
cp docs/workflows/templates/release.yml .github/workflows/

# Commit the workflows
git add .github/workflows/
git commit -m "feat: add GitHub Actions workflows for CI/CD automation"
git push
```

## 📋 Workflow Overview

### 1. **Continuous Integration** (`ci.yml`)
- **Multi-platform testing** (Ubuntu, Windows, macOS)
- **Python version matrix** (3.10, 3.11, 3.12) 
- **Code coverage** with Codecov integration
- **Performance benchmarking** with historical tracking
- **Pre-flight optimization** with change detection

### 2. **Security Scanning** (`security.yml`)
- **SAST scanning** (Bandit, Semgrep)
- **Dependency analysis** (pip-audit)
- **Container security** (Trivy)
- **SBOM generation** for compliance
- **Secrets detection** validation
- **License compliance** checking

### 3. **Release Automation** (`release.yml`)
- **Semantic versioning** automation
- **Automated changelog** generation
- **Multi-platform Docker** builds (AMD64, ARM64)
- **PyPI publishing** with trusted publishing
- **GitHub releases** with artifacts

## 🔧 Required Repository Configuration

### Secrets to Configure

Add these secrets in **Settings → Secrets and variables → Actions**:

```bash
# Code coverage
CODECOV_TOKEN=your_codecov_token_here

# Package publishing (optional - can use trusted publishing)
PYPI_API_TOKEN=your_pypi_token_here

# Container registry (optional)
DOCKER_HUB_USERNAME=your_dockerhub_username
DOCKER_HUB_TOKEN=your_dockerhub_token
```

### Repository Settings

1. **Enable Actions**: Settings → Actions → General → Allow all actions
2. **Workflow permissions**: Settings → Actions → General → Read and write permissions
3. **Branch protection**: Configure branch protection rules for `main`

## 🎯 Workflow Triggers

### CI Pipeline (`ci.yml`)
- **Push** to `main` and `develop` branches
- **Pull requests** to `main` branch
- **Weekly** security scans (Mondays at 2 AM UTC)

### Security Workflow (`security.yml`)
- **Push** to `main` and `develop` branches
- **Pull requests** to `main` branch
- **Daily** security scans (3 AM UTC)
- **Manual** workflow dispatch

### Release Pipeline (`release.yml`)
- **Git tags** matching pattern `v*.*.*`
- **Manual** workflow dispatch with version input

## 📊 Monitoring and Notifications

### Status Badges
Add these badges to your README.md:

```markdown
[![CI](https://github.com/your-org/agentic-redteam-radar/workflows/Continuous%20Integration/badge.svg)](https://github.com/your-org/agentic-redteam-radar/actions?query=workflow%3A%22Continuous+Integration%22)
[![Security](https://github.com/your-org/agentic-redteam-radar/workflows/Security%20Scan/badge.svg)](https://github.com/your-org/agentic-redteam-radar/actions?query=workflow%3A%22Security+Scan%22)
[![Release](https://github.com/your-org/agentic-redteam-radar/workflows/Release/badge.svg)](https://github.com/your-org/agentic-redteam-radar/actions?query=workflow%3ARelease)
```

### Failure Notifications
The security workflow automatically creates issues for failed scans with the `security` and `urgent` labels.

## 🔄 Workflow Customization

### Environment Variables
Customize these in each workflow file as needed:

```yaml
env:
  PYTHON_VERSION: '3.10'      # Primary Python version
  POETRY_VERSION: '1.6.1'     # Poetry version (if using)
  NODE_VERSION: '18'          # Node.js version (if needed)
```

### Test Configuration
Modify test commands in `ci.yml`:

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=agentic_redteam --cov-report=xml --cov-report=term-missing
```

### Security Tools
Add or remove security tools in `security.yml`:

```yaml
- name: Run additional security scanner
  run: |
    your-custom-security-tool --scan src/
```

## 🚀 Advanced Features

### Performance Benchmarking
The CI pipeline includes performance regression testing:
- Benchmarks are stored as GitHub artifacts
- Historical performance data is tracked
- Performance regressions trigger warnings

### Multi-Architecture Builds
Release pipeline builds for multiple architectures:
- Linux AMD64 (x86_64)
- Linux ARM64 (aarch64)
- Automatic platform detection

### Dependency Caching
All workflows include intelligent caching:
- Python dependencies cached by requirements hash
- Docker layer caching for faster builds
- Test result caching for unchanged code

## 📈 Metrics and Reporting

### Coverage Reports
- HTML coverage reports uploaded as artifacts
- Codecov integration for PR comments
- Coverage trend tracking

### Security Reports
- SARIF results uploaded to GitHub Security tab
- JSON reports available as downloadable artifacts
- Consolidated security dashboard

### Performance Metrics
- Benchmark results in JSON format
- Performance regression detection
- Historical performance visualization

---

**Note**: These workflows are designed for the Agentic RedTeam Radar project but can be adapted for other Python projects by modifying the package names and specific configurations.