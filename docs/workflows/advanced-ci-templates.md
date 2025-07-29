# Advanced CI/CD Workflow Templates

This document provides comprehensive GitHub Actions workflow templates designed for advanced Python security testing repositories. These templates build upon the existing CI/CD foundation with enhanced automation, security scanning, and deployment strategies.

## Enhanced Test Workflow

### `.github/workflows/test-advanced.yml`

```yaml
name: Advanced Test Suite
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:
    inputs:
      test_level:
        description: 'Test level to run'
        required: true
        default: 'standard'
        type: choice
        options:
          - standard
          - extended
          - performance
          - security

env:
  PYTHON_VERSION_DEFAULT: '3.10'
  CACHE_VERSION: v1

jobs:
  # Pre-flight checks
  pre-flight:
    name: Pre-flight Checks
    runs-on: ubuntu-latest
    outputs:
      python-versions: ${{ steps.setup.outputs.python-versions }}
      test-matrix: ${{ steps.setup.outputs.test-matrix }}
      skip-slow-tests: ${{ steps.setup.outputs.skip-slow-tests }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Setup test matrix
        id: setup
        run: |
          # Determine Python versions to test
          if [[ "${{ github.event_name }}" == "pull_request" ]]; then
            echo "python-versions=[\"3.10\"]" >> $GITHUB_OUTPUT
            echo "skip-slow-tests=true" >> $GITHUB_OUTPUT
          else
            echo "python-versions=[\"3.10\", \"3.11\", \"3.12\"]" >> $GITHUB_OUTPUT
            echo "skip-slow-tests=false" >> $GITHUB_OUTPUT
          fi
          
          # Setup test matrix based on input
          if [[ "${{ github.event.inputs.test_level }}" == "performance" ]]; then
            echo "test-matrix=[\"performance\"]" >> $GITHUB_OUTPUT
          elif [[ "${{ github.event.inputs.test_level }}" == "security" ]]; then
            echo "test-matrix=[\"security\"]" >> $GITHUB_OUTPUT
          else
            echo "test-matrix=[\"unit\", \"integration\"]" >> $GITHUB_OUTPUT
          fi

  # Code quality and linting
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    needs: pre-flight
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
          cache: 'pip'
          cache-dependency-path: |
            requirements.txt
            pyproject.toml
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      
      - name: Cache pre-commit
        uses: actions/cache@v3
        with:
          path: ~/.cache/pre-commit
          key: pre-commit-${{ env.CACHE_VERSION }}-${{ hashFiles('.pre-commit-config.yaml') }}
      
      - name: Run pre-commit
        run: pre-commit run --all-files --show-diff-on-failure
      
      - name: Run advanced linting
        run: |
          # Advanced code analysis
          pylint src/ --exit-zero --output-format=json > pylint-report.json
          
          # Code complexity analysis
          xenon --max-average A --max-modules B --max-absolute B src/
          
          # Security linting
          bandit -r src/ -f json -o bandit-report.json || true
      
      - name: Upload quality reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: quality-reports
          path: |
            pylint-report.json
            bandit-report.json

  # Dependency scanning
  dependency-scan:
    name: Dependency Security Scan
    runs-on: ubuntu-latest
    needs: pre-flight
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit --format=json --output=pip-audit.json || true
      
      - name: Run safety
        run: |
          pip install safety
          safety check --json --output safety-report.json || true
      
      - name: SBOM Generation
        run: |
          pip install cyclonedx-bom
          cyclonedx-py -o sbom.json
      
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: dependency-security
          path: |
            pip-audit.json
            safety-report.json
            sbom.json

  # Unit and integration tests
  test:
    name: Tests (Python ${{ matrix.python-version }}, ${{ matrix.test-type }})
    runs-on: ubuntu-latest
    needs: [pre-flight, quality]
    strategy:
      fail-fast: false
      matrix:
        python-version: ${{ fromJson(needs.pre-flight.outputs.python-versions) }}
        test-type: ${{ fromJson(needs.pre-flight.outputs.test-matrix) }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,test]"
      
      - name: Run tests
        run: |
          if [[ "${{ matrix.test-type }}" == "unit" ]]; then
            pytest tests/ -m "not integration and not performance" \
              --cov=agentic_redteam --cov-report=xml --cov-report=html \
              --junitxml=test-results-unit.xml
          elif [[ "${{ matrix.test-type }}" == "integration" ]]; then
            pytest tests/ -m "integration" \
              --cov=agentic_redteam --cov-report=xml \
              --junitxml=test-results-integration.xml
          elif [[ "${{ matrix.test-type }}" == "performance" ]]; then
            pytest tests/performance/ -m "performance and not load_test" \
              --benchmark-json=benchmark-results.json
          elif [[ "${{ matrix.test-type }}" == "security" ]]; then
            pytest tests/ -m "security" \
              --junitxml=test-results-security.xml
          fi
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results-${{ matrix.python-version }}-${{ matrix.test-type }}
          path: |
            test-results-*.xml
            htmlcov/
            benchmark-results.json
            coverage.xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        if: matrix.test-type == 'unit' && matrix.python-version == env.PYTHON_VERSION_DEFAULT
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

  # Performance benchmarking
  performance:
    name: Performance Benchmarks
    runs-on: ubuntu-latest
    needs: [pre-flight, quality]
    if: github.event.inputs.test_level == 'performance' || github.event_name == 'schedule'
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for performance comparison
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install pytest-benchmark memory-profiler py-spy
      
      - name: Run performance tests
        run: |
          pytest tests/performance/ -m "performance" \
            --benchmark-json=benchmark-results.json \
            --benchmark-min-rounds=5
      
      - name: Performance regression check
        run: |
          # Compare with previous results if available
          if [[ -f "benchmark-baseline.json" ]]; then
            python scripts/compare_benchmarks.py benchmark-baseline.json benchmark-results.json
          else
            echo "No baseline found, creating new baseline"
            cp benchmark-results.json benchmark-baseline.json
          fi
      
      - name: Upload performance results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: |
            benchmark-results.json
            performance_report.json

  # Load testing
  load-test:
    name: Load Testing
    runs-on: ubuntu-latest
    needs: [test]
    if: github.event.inputs.test_level == 'extended' || github.event_name == 'schedule'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      
      - name: Run load tests
        run: |
          export LOAD_CONCURRENT=50
          export LOAD_TOTAL=1000
          export LOAD_DURATION=60
          pytest tests/performance/ -m "load_test" -v
      
      - name: Upload load test results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: |
            load-test-report.json

  # Documentation and examples
  docs:
    name: Documentation
    runs-on: ubuntu-latest
    needs: pre-flight
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[docs]"
      
      - name: Build documentation
        run: |
          mkdocs build --strict
      
      - name: Test examples
        run: |
          # Test code examples in documentation
          python -m doctest README.md
          
          # Test example scripts
          if [[ -d "examples/" ]]; then
            python -m pytest examples/ --doctest-modules
          fi
      
      - name: Upload documentation
        uses: actions/upload-artifact@v3
        with:
          name: documentation
          path: site/

  # Final status check
  status-check:
    name: Status Check
    runs-on: ubuntu-latest
    needs: [quality, dependency-scan, test, docs]
    if: always()
    
    steps:
      - name: Check all jobs status
        run: |
          if [[ "${{ needs.quality.result }}" != "success" ]] || \
             [[ "${{ needs.dependency-scan.result }}" != "success" ]] || \
             [[ "${{ needs.test.result }}" != "success" ]] || \
             [[ "${{ needs.docs.result }}" != "success" ]]; then
            echo "One or more critical jobs failed"
            exit 1
          fi
          echo "All critical jobs passed"
      
      - name: Generate summary
        run: |
          echo "## Test Summary" >> $GITHUB_STEP_SUMMARY
          echo "- Quality: ${{ needs.quality.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Dependencies: ${{ needs.dependency-scan.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Tests: ${{ needs.test.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Documentation: ${{ needs.docs.result }}" >> $GITHUB_STEP_SUMMARY
```

## Advanced Security Workflow

### `.github/workflows/security-advanced.yml`

```yaml
name: Advanced Security Scanning
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 3 * * 1'  # Weekly on Monday at 3 AM UTC
  workflow_dispatch:

permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  # SAST (Static Application Security Testing)
  sast:
    name: Static Application Security Testing
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      
      - name: Run Bandit
        run: |
          pip install bandit[toml]
          bandit -r src/ -f sarif -o bandit-results.sarif
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/python
            p/owasp-top-ten
            p/cwe-top-25
          generateSarif: "1"
      
      - name: Upload SARIF results to GitHub
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: |
            bandit-results.sarif
            semgrep.sarif

  # CodeQL Analysis
  codeql:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    
    strategy:
      fail-fast: false
      matrix:
        language: [python]
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: ${{ matrix.language }}
          queries: security-extended,security-and-quality
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v2
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
        with:
          category: "/language:${{matrix.language}}"

  # Dependency vulnerability scanning
  dependency-scan:
    name: Dependency Vulnerability Scan
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit --format=sarif --output=pip-audit-results.sarif
        continue-on-error: true
      
      - name: Run Safety
        run: |
          pip install safety
          safety check --json --output=safety-results.json
        continue-on-error: true
      
      - name: Run OSV-Scanner
        uses: google/osv-scanner-action@v1
        with:
          scan-args: |-
            --format=sarif
            --output=osv-results.sarif
            ./
        continue-on-error: true
      
      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: |
            pip-audit-results.sarif
            osv-results.sarif

  # Container security scanning
  container-scan:
    name: Container Security Scan
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build -t agentic-redteam-radar:${{ github.sha }} .
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'agentic-redteam-radar:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # Secrets scanning
  secrets-scan:
    name: Secrets Scanning
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified

  # License compliance
  license-scan:
    name: License Compliance
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pip-licenses
      
      - name: Check licenses
        run: |
          pip-licenses --format=json --output-file=licenses.json
          
          # Check for forbidden licenses
          pip-licenses --fail-on="GPL-3.0;AGPL-3.0;LGPL-3.0"
      
      - name: Upload license report
        uses: actions/upload-artifact@v3
        with:
          name: license-report
          path: licenses.json

  # Security policy compliance
  compliance-check:
    name: Security Policy Compliance
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Check required security files
        run: |
          # Check for required security files
          required_files=(
            "SECURITY.md"
            "CODE_OF_CONDUCT.md"
            ".pre-commit-config.yaml"
            "pyproject.toml"
          )
          
          missing_files=()
          for file in "${required_files[@]}"; do
            if [[ ! -f "$file" ]]; then
              missing_files+=("$file")
            fi
          done
          
          if [[ ${#missing_files[@]} -gt 0 ]]; then
            echo "Missing required security files:"
            printf '%s\n' "${missing_files[@]}"
            exit 1
          fi
          
          echo "All required security files present"
      
      - name: Validate security configuration
        run: |
          # Check pyproject.toml for security settings
          python -c "
          import toml
          config = toml.load('pyproject.toml')
          
          # Check for bandit configuration
          assert 'tool' in config and 'bandit' in config['tool'], 'Bandit configuration missing'
          
          # Check for security dependencies in dev requirements
          dev_deps = config.get('project', {}).get('optional-dependencies', {}).get('dev', [])
          security_tools = ['bandit', 'safety', 'pip-audit']
          
          for tool in security_tools:
            assert any(tool in dep for dep in dev_deps), f'{tool} not in dev dependencies'
          
          print('Security configuration validated')
          "

  # Generate security summary
  security-summary:
    name: Security Summary
    runs-on: ubuntu-latest
    needs: [sast, codeql, dependency-scan, secrets-scan, license-scan, compliance-check]
    if: always()
    
    steps:
      - name: Generate security summary
        run: |
          echo "## Security Scan Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Scan Type | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-----------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| SAST | ${{ needs.sast.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| CodeQL | ${{ needs.codeql.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Dependencies | ${{ needs.dependency-scan.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Secrets | ${{ needs.secrets-scan.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Licenses | ${{ needs.license-scan.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Compliance | ${{ needs.compliance-check.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          # Check if all critical scans passed
          if [[ "${{ needs.sast.result }}" == "success" ]] && \
             [[ "${{ needs.codeql.result }}" == "success" ]] && \
             [[ "${{ needs.dependency-scan.result }}" == "success" ]] && \
             [[ "${{ needs.compliance-check.result }}" == "success" ]]; then
            echo "✅ All critical security scans passed" >> $GITHUB_STEP_SUMMARY
          else
            echo "❌ One or more critical security scans failed" >> $GITHUB_STEP_SUMMARY
          fi
```

## Release Automation Workflow

### `.github/workflows/release-automation.yml`

```yaml
name: Release Automation
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release (e.g., 1.0.0)'
        required: true
      release_type:
        description: 'Type of release'
        required: true
        default: 'minor'
        type: choice
        options:
          - patch
          - minor
          - major
          - prerelease

env:
  PYTHON_VERSION: '3.10'

jobs:
  # Validate release
  validate-release:
    name: Validate Release
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      is_prerelease: ${{ steps.version.outputs.is_prerelease }}
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Determine version
        id: version
        run: |
          if [[ "${{ github.event_name }}" == "push" ]]; then
            # Extract version from tag
            VERSION=${GITHUB_REF#refs/tags/v}
          else
            # Use manual input
            VERSION="${{ github.event.inputs.version }}"
          fi
          
          echo "version=${VERSION}" >> $GITHUB_OUTPUT
          
          # Check if prerelease
          if [[ "$VERSION" =~ -.*$ ]]; then
            echo "is_prerelease=true" >> $GITHUB_OUTPUT
          else
            echo "is_prerelease=false" >> $GITHUB_OUTPUT
          fi
          
          echo "Release version: $VERSION"
      
      - name: Validate version format
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-.*)?$ ]]; then
            echo "Invalid version format: $VERSION"
            exit 1
          fi
      
      - name: Check if tag exists
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          if git rev-parse "v$VERSION" >/dev/null 2>&1; then
            echo "Tag v$VERSION already exists"
            exit 1
          fi

  # Run comprehensive tests
  test-release:
    name: Test Release
    needs: validate-release
    uses: ./.github/workflows/test-advanced.yml
    with:
      test_level: extended

  # Build and test package
  build-package:
    name: Build Package
    runs-on: ubuntu-latest
    needs: [validate-release, test-release]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine
      
      - name: Update version
        run: |
          VERSION="${{ needs.validate-release.outputs.version }}"
          # Update version in pyproject.toml
          sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
          
          # Update version in __init__.py if it exists
          if [[ -f "src/agentic_redteam/__init__.py" ]]; then
            sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/agentic_redteam/__init__.py
          fi
      
      - name: Build package
        run: |
          python -m build
      
      - name: Verify package
        run: |
          twine check dist/*
          
          # Test installation
          pip install dist/*.whl
          python -c "import agentic_redteam; print('Package installed successfully')"
      
      - name: Upload package artifacts
        uses: actions/upload-artifact@v3
        with:
          name: package-artifacts
          path: dist/
          retention-days: 30

  # Generate release notes
  generate-release-notes:
    name: Generate Release Notes
    runs-on: ubuntu-latest
    needs: validate-release
    outputs:
      release-notes: ${{ steps.notes.outputs.release-notes }}
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Generate release notes
        id: notes
        run: |
          VERSION="${{ needs.validate-release.outputs.version }}"
          
          # Get previous tag
          PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "")
          
          if [[ -n "$PREV_TAG" ]]; then
            # Generate changelog from commits
            echo "## What's Changed" > RELEASE_NOTES.md
            echo "" >> RELEASE_NOTES.md
            
            # Get commits since last tag
            git log --pretty=format:"- %s by @%an" "${PREV_TAG}..HEAD" >> RELEASE_NOTES.md
            
            echo "" >> RELEASE_NOTES.md
            echo "**Full Changelog**: https://github.com/${{ github.repository }}/compare/${PREV_TAG}...v${VERSION}" >> RELEASE_NOTES.md
          else
            echo "## Initial Release" > RELEASE_NOTES.md
            echo "" >> RELEASE_NOTES.md
            echo "This is the initial release of Agentic RedTeam Radar." >> RELEASE_NOTES.md
          fi
          
          # Output for next step
          cat RELEASE_NOTES.md
          echo "release-notes<<EOF" >> $GITHUB_OUTPUT
          cat RELEASE_NOTES.md >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      
      - name: Upload release notes
        uses: actions/upload-artifact@v3
        with:
          name: release-notes
          path: RELEASE_NOTES.md

  # Create GitHub release
  create-release:
    name: Create GitHub Release
    runs-on: ubuntu-latest
    needs: [validate-release, build-package, generate-release-notes]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Download package artifacts
        uses: actions/download-artifact@v3
        with:
          name: package-artifacts
          path: dist/
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ needs.validate-release.outputs.version }}
          release_name: Release v${{ needs.validate-release.outputs.version }}
          body: ${{ needs.generate-release-notes.outputs.release-notes }}
          draft: false
          prerelease: ${{ needs.validate-release.outputs.is_prerelease }}
      
      - name: Upload Release Assets
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: dist/
          asset_name: release-artifacts
          asset_content_type: application/zip

  # Publish to PyPI
  publish-pypi:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    needs: [validate-release, create-release]
    if: ${{ !needs.validate-release.outputs.is_prerelease }}
    environment:
      name: pypi
      url: https://pypi.org/p/agentic-redteam-radar
    
    steps:
      - name: Download package artifacts
        uses: actions/download-artifact@v3
        with:
          name: package-artifacts
          path: dist/
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
          verbose: true

  # Publish to Test PyPI (for prereleases)
  publish-test-pypi:
    name: Publish to Test PyPI
    runs-on: ubuntu-latest
    needs: [validate-release, create-release]
    if: ${{ needs.validate-release.outputs.is_prerelease }}
    
    steps:
      - name: Download package artifacts
        uses: actions/download-artifact@v3
        with:
          name: package-artifacts
          path: dist/
      
      - name: Publish to Test PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.TEST_PYPI_API_TOKEN }}
          repository_url: https://test.pypi.org/legacy/
          verbose: true

  # Post-release tasks
  post-release:
    name: Post-Release Tasks
    runs-on: ubuntu-latest
    needs: [validate-release, publish-pypi, publish-test-pypi]
    if: always() && (needs.publish-pypi.result == 'success' || needs.publish-test-pypi.result == 'success')
    
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Update development version
        if: ${{ !needs.validate-release.outputs.is_prerelease }}
        run: |
          # Bump version for next development cycle
          VERSION="${{ needs.validate-release.outputs.version }}"
          IFS='.' read -r major minor patch <<< "$VERSION"
          
          # Increment minor version and add dev suffix
          NEXT_VERSION="$major.$((minor + 1)).0.dev0"
          
          # Update version in pyproject.toml
          sed -i "s/version = \".*\"/version = \"$NEXT_VERSION\"/" pyproject.toml
          
          # Commit changes
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add pyproject.toml
          git commit -m "Bump version to $NEXT_VERSION for development"
          git push
      
      - name: Create milestone for next version
        if: ${{ !needs.validate-release.outputs.is_prerelease }}
        uses: actions/github-script@v6
        with:
          script: |
            const version = "${{ needs.validate-release.outputs.version }}";
            const [major, minor, patch] = version.split('.').map(Number);
            const nextVersion = `${major}.${minor + 1}.0`;
            
            await github.rest.issues.createMilestone({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `v${nextVersion}`,
              description: `Milestone for version ${nextVersion}`
            });

  # Notify stakeholders
  notify:
    name: Notify Stakeholders
    runs-on: ubuntu-latest
    needs: [validate-release, post-release]
    if: always() && needs.post-release.result == 'success'
    
    steps:
      - name: Send notification
        run: |
          VERSION="${{ needs.validate-release.outputs.version }}"
          IS_PRERELEASE="${{ needs.validate-release.outputs.is_prerelease }}"
          
          if [[ "$IS_PRERELEASE" == "true" ]]; then
            RELEASE_TYPE="pre-release"
          else
            RELEASE_TYPE="stable release"
          fi
          
          echo "🎉 Agentic RedTeam Radar v$VERSION has been successfully released as a $RELEASE_TYPE!"
          echo "📦 Available on PyPI: https://pypi.org/project/agentic-redteam-radar/$VERSION/"
          echo "📋 Release notes: https://github.com/${{ github.repository }}/releases/tag/v$VERSION"
```

## Manual Setup Instructions

1. **Create Workflow Directory**:
   ```bash
   mkdir -p .github/workflows
   ```

2. **Copy Workflow Templates**:
   - Copy the YAML content above into respective workflow files
   - Customize the workflows based on your specific needs

3. **Required Repository Secrets**:
   - `PYPI_API_TOKEN`: For publishing to PyPI
   - `TEST_PYPI_API_TOKEN`: For publishing to Test PyPI
   - `CODECOV_TOKEN`: For coverage reporting

4. **Required Repository Settings**:
   - Enable GitHub Actions
   - Configure branch protection rules
   - Set up environments (pypi) with deployment protection rules

## Key Features

### Advanced Test Workflow
- **Matrix Testing**: Multiple Python versions and test types
- **Performance Benchmarking**: Automated performance regression detection
- **Load Testing**: Sustained load testing capabilities
- **Documentation Testing**: Validates examples and documentation

### Security Workflow
- **Multi-tool SAST**: Bandit, Semgrep, and CodeQL
- **Dependency Scanning**: pip-audit, Safety, and OSV-Scanner
- **Container Security**: Trivy scanning for container images
- **License Compliance**: Automated license checking
- **Secrets Detection**: TruffleHog for secret scanning

### Release Automation
- **Automated Versioning**: Semantic version management
- **Comprehensive Testing**: Full test suite before release
- **Package Building**: Automated wheel and source distribution creation
- **Release Notes**: Auto-generated changelog from commits
- **Multi-environment Publishing**: PyPI and Test PyPI support
- **Post-release Tasks**: Version bumping and milestone creation

These templates provide enterprise-grade CI/CD automation suitable for advanced Python security testing repositories.