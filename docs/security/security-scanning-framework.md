# Security Scanning and Compliance Framework

This document outlines the comprehensive security scanning and compliance framework for the Agentic RedTeam Radar project. It includes configurations, policies, and procedures for maintaining security throughout the development lifecycle.

## Framework Overview

The security framework implements defense-in-depth through multiple scanning layers:

1. **Static Application Security Testing (SAST)**
2. **Dynamic Application Security Testing (DAST)**
3. **Dependency Vulnerability Scanning**
4. **Container Security Scanning**
5. **Infrastructure as Code (IaC) Security**
6. **Secrets Detection**
7. **Compliance Monitoring**

## Configuration Files

### Bandit Configuration (pyproject.toml)

```toml
[tool.bandit]
exclude_dirs = ["tests", "test_*", "*_test.py", "venv", ".venv"]
skips = ["B101", "B601"]  # Skip assert statements and paramiko usage

[tool.bandit.assert_used]
skips = ["*_test.py", "test_*.py", "tests/*"]

# Security issue patterns to ignore in specific contexts
[tool.bandit.hardcoded_password_string]
word_list = ["password", "pass", "pwd", "secret", "token", "key"]

[tool.bandit.hardcoded_password_funcarg]
word_list = ["password", "pass", "pwd", "secret", "token", "key"]

[tool.bandit.hardcoded_password_default]
word_list = ["password", "pass", "pwd", "secret", "token", "key"]
```

### pip-audit Configuration

```toml
[tool.pip-audit]
# Ignore advisories that don't apply to our use case
ignore-vulns = []
# Set vulnerability database
index-url = "https://pypi.org/simple/"
# Output format options
format = "json"
# Fail on any vulnerability
require-hashes = false
```

### Safety Configuration

```toml
[tool.safety]
# Ignore specific vulnerability IDs if they don't apply
ignore = []
# Full report mode
full-report = true
# Check installed packages
check-installed = true
```

### Semgrep Configuration

```yaml
# .semgrep.yml
rules:
  - id: hardcoded-secret
    patterns:
      - pattern: $VAR = "..."
      - metavariable-regex:
          metavariable: $VAR
          regex: (?i)(password|secret|token|key|api_key)
    message: "Potential hardcoded secret detected"
    languages: [python]
    severity: ERROR

  - id: sql-injection
    patterns:
      - pattern: $CURSOR.execute($QUERY % $VAR)
      - pattern: $CURSOR.execute($QUERY + $VAR)
      - pattern: $CURSOR.execute(f"... {$VAR} ...")
    message: "Potential SQL injection vulnerability"
    languages: [python]
    severity: ERROR

  - id: command-injection
    patterns:
      - pattern: os.system($CMD)
      - pattern: subprocess.call($CMD, shell=True)
      - pattern: subprocess.run($CMD, shell=True)
    message: "Potential command injection vulnerability"
    languages: [python]
    severity: ERROR

  - id: insecure-random
    patterns:
      - pattern: random.random()
      - pattern: random.choice(...)
      - pattern: random.randint(...)
    message: "Use secrets module for cryptographic randomness"
    languages: [python]
    severity: WARNING

  - id: eval-usage
    patterns:
      - pattern: eval(...)
      - pattern: exec(...)
    message: "Avoid using eval() and exec()"
    languages: [python]
    severity: ERROR

  - id: pickle-usage
    patterns:
      - pattern: pickle.loads(...)
      - pattern: cPickle.loads(...)
    message: "Pickle can execute arbitrary code during deserialization"
    languages: [python]
    severity: WARNING

  - id: weak-crypto
    patterns:
      - pattern: hashlib.md5(...)
      - pattern: hashlib.sha1(...)
    message: "Use stronger hash algorithms (SHA-256 or better)"
    languages: [python]
    severity: WARNING

  - id: debug-mode
    patterns:
      - pattern: app.run(debug=True)
      - pattern: DEBUG = True
    message: "Debug mode should not be enabled in production"
    languages: [python]
    severity: ERROR
```

### CodeQL Configuration

```yaml
# .github/codeql/codeql-config.yml
name: "Security Scanning Configuration"

queries:
  - uses: security-extended
  - uses: security-and-quality

paths-ignore:
  - tests/
  - docs/
  - examples/

paths:
  - src/

# Custom query packs
packs:
  - codeql/python-queries:Experimental
  - codeql/python-queries:Security
```

## Security Policies

### Security Policy Template

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| 0.x.x   | :x:                |

## Reporting a Vulnerability

To report a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security@agentic-redteam.org with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested remediation

We aim to respond within 24 hours and provide a fix within 7 days for critical issues.

## Security Measures

- All dependencies are scanned for vulnerabilities
- Static code analysis is performed on every commit
- Secrets are managed through environment variables
- Access to production resources requires multi-factor authentication
- All data transmission uses TLS 1.3 or higher
```

### Vulnerability Management Process

```yaml
# docs/security/vulnerability-management.yml
vulnerability_management:
  discovery:
    automated_scanning:
      - dependency_scanning: daily
      - static_analysis: on_commit
      - container_scanning: on_build
      - infrastructure_scanning: weekly
    
    manual_testing:
      - penetration_testing: quarterly
      - code_review: on_pull_request
      - security_architecture_review: on_major_changes
  
  assessment:
    severity_levels:
      critical:
        description: "Immediate threat to production systems"
        response_time: "4 hours"
        fix_time: "24 hours"
      
      high:
        description: "Significant security risk"
        response_time: "24 hours"
        fix_time: "7 days"
      
      medium:
        description: "Moderate security risk"
        response_time: "3 days"
        fix_time: "30 days"
      
      low:
        description: "Minor security issue"
        response_time: "7 days"
        fix_time: "90 days"
  
  remediation:
    process:
      1. "Immediate containment if needed"
      2. "Develop and test fix"
      3. "Deploy fix to production"
      4. "Verify fix effectiveness"
      5. "Update documentation"
      6. "Conduct post-incident review"
  
  communication:
    internal:
      - security_team: "immediate"
      - development_team: "within 4 hours"
      - management: "within 24 hours"
    
    external:
      - customers: "as required by law/contract"
      - vendors: "if third-party vulnerability"
      - public: "coordinated disclosure if applicable"
```

## Compliance Framework

### OWASP Top 10 Mapping

```yaml
# docs/security/owasp-top-10-mapping.yml
owasp_top_10_2021:
  A01_broken_access_control:
    controls:
      - "Role-based access control implementation"
      - "Principle of least privilege"
      - "Authentication and authorization testing"
    
    scanning:
      - bandit: "B106,B107,B108"
      - semgrep: "access-control-*"
      - manual: "Penetration testing"
  
  A02_cryptographic_failures:
    controls:
      - "Strong encryption algorithms"
      - "Proper key management"
      - "TLS for data in transit"
    
    scanning:
      - bandit: "B303,B304,B305,B306,B307"
      - semgrep: "crypto-*"
      - ssl_labs: "TLS configuration"
  
  A03_injection:
    controls:
      - "Input validation"
      - "Parameterized queries"
      - "Output encoding"
    
    scanning:
      - bandit: "B608,B609,B610,B611"
      - semgrep: "injection-*"
      - dynamic: "DAST tools"
  
  A04_insecure_design:
    controls:
      - "Threat modeling"
      - "Security architecture review"
      - "Secure design patterns"
    
    scanning:
      - manual: "Architecture review"
      - threat_modeling: "Regular sessions"
  
  A05_security_misconfiguration:
    controls:
      - "Secure defaults"
      - "Configuration management"
      - "Regular security updates"
    
    scanning:
      - bandit: "B105,B106,B108"
      - infrastructure: "Config scanning"
  
  A06_vulnerable_components:
    controls:
      - "Dependency management"
      - "Regular updates"
      - "Vulnerability scanning"
    
    scanning:
      - pip_audit: "Python dependencies"
      - safety: "Known vulnerabilities"
      - snyk: "Third-party libraries"
  
  A07_identification_failures:
    controls:
      - "Strong authentication"
      - "Session management"
      - "Multi-factor authentication"
    
    scanning:
      - bandit: "B105,B106"
      - manual: "Authentication testing"
  
  A08_software_integrity:
    controls:
      - "Code signing"
      - "Supply chain security"
      - "Integrity checks"
    
    scanning:
      - sbom: "Software bill of materials"
      - signing: "Artifact verification"
  
  A09_logging_failures:
    controls:
      - "Comprehensive logging"
      - "Log monitoring"
      - "Incident response"
    
    scanning:
      - bandit: "B201,B202"
      - manual: "Log review"
  
  A10_ssrf:
    controls:
      - "Input validation"
      - "Network segmentation"
      - "Allowlist validation"
    
    scanning:
      - semgrep: "ssrf-*"
      - dynamic: "SSRF testing"
```

### Compliance Checklist

```yaml
# docs/security/compliance-checklist.yml
security_compliance:
  code_security:
    - name: "Static code analysis enabled"
      status: "required"
      tools: ["bandit", "semgrep", "codeql"]
    
    - name: "Dependency vulnerability scanning"
      status: "required"
      tools: ["pip-audit", "safety", "snyk"]
    
    - name: "Secrets detection"
      status: "required"
      tools: ["detect-secrets", "trufflehog"]
    
    - name: "Code review process"
      status: "required"
      process: "All code changes require review"
  
  infrastructure_security:
    - name: "Container vulnerability scanning"
      status: "required"
      tools: ["trivy", "snyk"]
    
    - name: "IaC security scanning"
      status: "required"
      tools: ["checkov", "tfsec"]
    
    - name: "Network security"
      status: "required"
      controls: ["TLS 1.3", "VPN access", "Firewall rules"]
  
  operational_security:
    - name: "Incident response plan"
      status: "required"
      documentation: "docs/security/incident-response.md"
    
    - name: "Security training"
      status: "required"
      frequency: "quarterly"
    
    - name: "Vulnerability disclosure"
      status: "required"
      policy: "SECURITY.md"
  
  data_protection:
    - name: "Data classification"
      status: "required"
      levels: ["public", "internal", "confidential", "restricted"]
    
    - name: "Encryption at rest"
      status: "required"
      algorithms: ["AES-256"]
    
    - name: "Encryption in transit"
      status: "required"
      protocols: ["TLS 1.3"]
```

## Security Testing Automation

### Security Test Pipeline

```yaml
# .github/workflows/security-pipeline.yml
name: Security Testing Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  security-gate:
    name: Security Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Security Baseline Check
        run: |
          # Check for required security files
          required_files=(
            "SECURITY.md"
            ".secrets.baseline"
            "docs/security/security-scanning-framework.md"
          )
          
          for file in "${required_files[@]}"; do
            if [[ ! -f "$file" ]]; then
              echo "❌ Missing required security file: $file"
              exit 1
            fi
          done
          
          echo "✅ All required security files present"
      
      - name: Run Security Scorecard
        uses: ossf/scorecard-action@v2
        with:
          results_file: scorecard-results.sarif
          results_format: sarif
          publish_results: true
      
      - name: Upload Scorecard Results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: scorecard-results.sarif

  sast-comprehensive:
    name: Comprehensive SAST
    runs-on: ubuntu-latest
    needs: security-gate
    strategy:
      matrix:
        tool: [bandit, semgrep, codeql]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Run Bandit
        if: matrix.tool == 'bandit'
        run: |
          pip install bandit[toml]
          bandit -r src/ -f sarif -o bandit-results.sarif
      
      - name: Run Semgrep
        if: matrix.tool == 'semgrep'
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/owasp-top-ten
            p/cwe-top-25
            .semgrep.yml
          generateSarif: "1"
      
      - name: Initialize CodeQL
        if: matrix.tool == 'codeql'
        uses: github/codeql-action/init@v2
        with:
          languages: python
          config-file: .github/codeql/codeql-config.yml
      
      - name: Perform CodeQL Analysis
        if: matrix.tool == 'codeql'
        uses: github/codeql-action/analyze@v2
      
      - name: Upload SARIF results
        if: always()
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: ${{ matrix.tool }}-results.sarif

  dependency-security:
    name: Dependency Security Analysis
    runs-on: ubuntu-latest
    needs: security-gate
    
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
          safety check --json --output=safety-results.json --continue-on-error
        continue-on-error: true
      
      - name: Generate SBOM
        run: |
          pip install cyclonedx-bom
          cyclonedx-py -o sbom.json
      
      - name: Upload Security Reports
        uses: actions/upload-artifact@v3
        with:
          name: dependency-security-reports
          path: |
            pip-audit-results.sarif
            safety-results.json
            sbom.json
      
      - name: Upload SARIF results
        if: always()
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: pip-audit-results.sarif

  secrets-scanning:
    name: Secrets Detection
    runs-on: ubuntu-latest
    needs: security-gate
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Run detect-secrets
        run: |
          pip install detect-secrets
          detect-secrets scan --baseline .secrets.baseline --all-files
      
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified

  container-security:
    name: Container Security Scan
    runs-on: ubuntu-latest
    needs: security-gate
    if: github.event_name != 'pull_request'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build -t agentic-redteam-radar:security-scan .
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'agentic-redteam-radar:security-scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  security-summary:
    name: Security Summary
    runs-on: ubuntu-latest
    needs: [sast-comprehensive, dependency-security, secrets-scanning, container-security]
    if: always()
    
    steps:
      - name: Generate Security Summary
        run: |
          echo "## 🛡️ Security Scan Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Scan Type | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-----------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| SAST | ${{ needs.sast-comprehensive.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Dependencies | ${{ needs.dependency-security.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Secrets | ${{ needs.secrets-scanning.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Container | ${{ needs.container-security.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          # Overall status
          if [[ "${{ needs.sast-comprehensive.result }}" == "success" && \
                "${{ needs.dependency-security.result }}" == "success" && \
                "${{ needs.secrets-scanning.result }}" == "success" ]]; then
            echo "✅ **All critical security scans passed**" >> $GITHUB_STEP_SUMMARY
          else
            echo "❌ **One or more security scans failed**" >> $GITHUB_STEP_SUMMARY
          fi
```

## Monitoring and Alerting

### Security Metrics Dashboard

```yaml
# docs/security/security-metrics.yml
security_metrics:
  vulnerability_metrics:
    - name: "Critical vulnerabilities"
      threshold: 0
      action: "Block deployment"
    
    - name: "High vulnerabilities"
      threshold: 3
      action: "Require approval"
    
    - name: "Mean time to fix (MTTF)"
      target: "< 7 days"
      measurement: "From discovery to remediation"
  
  code_quality_metrics:
    - name: "Security issues per 1000 lines"
      target: "< 1"
      tools: ["bandit", "semgrep"]
    
    - name: "Test coverage"
      minimum: "80%"
      security_tests: "Required"
  
  operational_metrics:
    - name: "Failed login attempts"
      threshold: 10
      timeframe: "5 minutes"
    
    - name: "Unusual API access patterns"
      detection: "Machine learning"
      action: "Alert security team"

alerts:
  critical:
    - "New critical vulnerability discovered"
    - "Secrets detected in code"
    - "Security test failures"
    - "Unusual system behavior"
  
  warning:
    - "New high vulnerability discovered"
    - "Dependency updates available"
    - "Security policy violations"
  
  info:
    - "Security scan completed"
    - "New security advisories"
    - "Compliance report generated"
```

This comprehensive security scanning and compliance framework provides enterprise-grade security controls for the Agentic RedTeam Radar project, ensuring robust protection throughout the development lifecycle.