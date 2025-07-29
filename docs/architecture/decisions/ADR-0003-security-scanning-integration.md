# ADR-0003: Security Scanning Integration

## Status
Accepted

## Context

The Agentic RedTeam Radar project requires comprehensive security scanning integration to ensure the security scanner itself is secure and compliant with enterprise security standards. The project needs to integrate with multiple security tools and workflows while maintaining high security standards throughout the development lifecycle.

Key requirements:
- **Static Application Security Testing (SAST)**: Scan source code for security vulnerabilities
- **Dynamic Application Security Testing (DAST)**: Test running application for runtime vulnerabilities
- **Dependency Scanning**: Identify vulnerable dependencies and supply chain risks
- **Container Security**: Scan container images for vulnerabilities and misconfigurations
- **Infrastructure as Code (IaC)**: Validate infrastructure configurations for security best practices
- **Secrets Detection**: Prevent accidental commit of sensitive information
- **Compliance**: Meet industry standards (OWASP, NIST, SOC 2)

Challenges:
- Multiple security tools with different formats and interfaces
- Integration with CI/CD pipeline without blocking development velocity
- False positive management and vulnerability prioritization
- Security tool maintenance and updates
- Compliance reporting and audit trail requirements
- Developer experience and security tooling adoption

## Considered Options

### Option 1: Single Security Platform
- Use comprehensive security platform (e.g., Snyk, Veracode, Checkmarx)
- Unified dashboard and reporting
- Single vendor relationship and support

**Pros:**
- Simplified management and configuration
- Unified reporting and analytics
- Consistent user experience across security domains
- Better correlation between different scan types
- Single point of contact for support

**Cons:**
- Vendor lock-in and potential cost escalation
- May not be best-in-class for all security domains
- Limited customization and extensibility
- Risk of single point of failure
- Potential gaps in specialized security testing

### Option 2: Best-of-Breed Multi-Tool Approach (Chosen)
- Select specialized tools for each security domain
- Custom integration and orchestration layer
- Unified reporting through centralized dashboard
- Flexible tool replacement and evolution

**Pros:**
- Best-in-class tools for each security domain
- Flexibility to adapt and change tools as needed
- No vendor lock-in risk
- Customizable integration and workflows
- Cost optimization through tool selection

**Cons:**
- Increased complexity in integration and maintenance
- Multiple vendor relationships to manage
- Potential inconsistencies in reporting formats
- More complex configuration and setup
- Higher operational overhead

### Option 3: Hybrid Approach
- Primary security platform for core scanning
- Specialized tools for specific domains
- Custom integrations where needed

**Pros:**
- Balanced approach with reduced complexity
- Flexibility for specialized requirements
- Reduced vendor lock-in compared to single platform
- Manageable operational overhead

**Cons:**
- Still some vendor dependency
- Complexity in tool interactions
- Potential gaps between platform and specialized tools
- Mixed support experiences

## Decision

We will implement a **Best-of-Breed Multi-Tool Approach** with the following security scanning stack:

### Static Application Security Testing (SAST)
- **Primary**: Bandit (Python-specific SAST)
- **Secondary**: Semgrep (custom rule engine)
- **Enterprise**: CodeQL (GitHub native integration)
- **Linting**: pylint, flake8 with security plugins

### Dynamic Application Security Testing (DAST)
- **API Testing**: OWASP ZAP for REST API security testing
- **Container Testing**: Custom health check and penetration testing
- **Load Testing**: Locust with security-focused scenarios

### Dependency Scanning
- **Python Dependencies**: pip-audit, Safety
- **License Compliance**: pip-licenses
- **Supply Chain**: OSV-Scanner, Snyk (free tier)
- **SBOM Generation**: CycloneDX tools

### Container Security
- **Image Scanning**: Trivy (comprehensive vulnerability scanner)
- **Runtime Security**: Falco (runtime threat detection)
- **Configuration**: Docker Bench Security

### Infrastructure as Code (IaC)
- **Terraform**: tfsec, Checkov
- **Kubernetes**: kube-score, Polaris
- **Docker**: Hadolint for Dockerfile scanning

### Secrets Detection
- **Pre-commit**: detect-secrets baseline
- **Repository Scanning**: TruffleHog
- **CI/CD Integration**: GitLeaks

### Integration Architecture

```yaml
# Security scanning pipeline architecture
security_pipeline:
  stages:
    pre_commit:
      tools: [detect-secrets, bandit-baseline]
      blocking: yes
      
    code_analysis:
      parallel:
        - sast: [bandit, semgrep, codeql]
        - dependencies: [pip-audit, safety, osv-scanner]
        - secrets: [trufflehog, gitleaks]
      blocking: yes
      
    build_security:
      tools: [trivy-fs, hadolint]
      blocking: yes
      
    post_build:
      tools: [trivy-image, container-security-scan]
      blocking: conditionally
      
    deployment:
      tools: [dast-api, infrastructure-scan]
      blocking: no
      monitoring: yes

  reporting:
    formats: [sarif, json, html]
    destinations: [github-security, dashboard, slack]
    
  thresholds:
    critical: 0
    high: 3
    medium: 10
    
  exceptions:
    management: security-team-approval
    tracking: github-issues
    expiration: 90-days
```

## Rationale

### Tool Selection Criteria
Each tool was selected based on:
- **Effectiveness**: High detection rate with low false positives
- **Integration**: Good CI/CD integration and API support
- **Maintenance**: Active development and security updates
- **Cost**: Open source or reasonable licensing costs
- **Community**: Strong community support and documentation

### Multi-Tool Benefits
- **Depth**: Specialized tools provide deeper analysis in their domain
- **Breadth**: Comprehensive coverage across all security domains
- **Flexibility**: Easy to replace or upgrade individual tools
- **Innovation**: Adopt new tools and techniques as they emerge
- **Risk Distribution**: No single point of failure or vendor dependency

### Integration Strategy
- **Standardized Output**: SARIF format for consistent result processing
- **Centralized Orchestration**: Single pipeline coordinating all tools
- **Flexible Configuration**: Tool-specific configuration with global policies
- **Unified Reporting**: Aggregated dashboard with drill-down capabilities

## Consequences

### Positive
- **Comprehensive Coverage**: Best-in-class tools for each security domain
- **Flexibility**: Easy tool replacement and configuration changes
- **Cost Control**: Open source tools reduce licensing costs
- **Innovation Adoption**: Quick adoption of new security tools and techniques
- **No Vendor Lock-in**: Independence from any single security vendor
- **Customization**: Tailored security policies and rule sets
- **Developer Integration**: Rich IDE and pre-commit integration

### Negative
- **Complexity**: Multiple tools require more configuration and maintenance
- **Integration Overhead**: Custom integration logic needed for each tool
- **Inconsistent UX**: Different interfaces and workflows for each tool
- **Alert Fatigue**: Multiple tools may generate overlapping alerts
- **Maintenance Burden**: Keeping multiple tools updated and configured
- **Skill Requirements**: Team needs expertise across multiple security tools

### Neutral
- **Tool Evolution**: Regular evaluation needed for tool effectiveness
- **Configuration Management**: Infrastructure-as-code for tool configurations
- **Training Requirements**: Team training on security tools and processes

## Implementation

### Phase 1: Core SAST Integration (Week 1)
- [ ] Configure Bandit with custom rules and baseline
- [ ] Integrate Semgrep with security-focused rule sets
- [ ] Set up CodeQL for GitHub integration
- [ ] Implement SARIF result aggregation and processing

### Phase 2: Dependency and Supply Chain Security (Week 2)
- [ ] Configure pip-audit and Safety for dependency scanning
- [ ] Set up OSV-Scanner for comprehensive vulnerability detection
- [ ] Implement SBOM generation with CycloneDX
- [ ] Create supply chain risk assessment reporting

### Phase 3: Container and Infrastructure Security (Week 3)
- [ ] Integrate Trivy for container image scanning
- [ ] Configure Hadolint for Dockerfile security analysis
- [ ] Set up infrastructure scanning for Terraform/Kubernetes
- [ ] Implement container runtime security monitoring

### Phase 4: Secrets and Dynamic Testing (Week 4)
- [ ] Deploy detect-secrets and TruffleHog integration
- [ ] Configure OWASP ZAP for API security testing
- [ ] Set up automated penetration testing scenarios
- [ ] Implement security regression testing

### Phase 5: Reporting and Monitoring (Week 5)
- [ ] Build unified security dashboard with Grafana
- [ ] Implement security metrics and KPI tracking
- [ ] Set up automated security reporting
- [ ] Configure alerting and incident response integration

### Security Tool Configuration

#### Bandit Configuration
```toml
[tool.bandit]
exclude_dirs = ["tests", "test_*", "*_test.py"]
skips = ["B101", "B601"]  # Skip assert statements and paramiko
confidence_level = "medium"
severity_level = "medium"

[tool.bandit.hardcoded_password_string]
word_list = ["password", "pass", "pwd", "secret", "token", "key"]
```

#### Semgrep Rules
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
```

#### Trivy Configuration
```yaml
# trivy.yaml
vulnerability:
  type: os,library
severity: CRITICAL,HIGH,MEDIUM
format: sarif
output: trivy-results.sarif
```

### Security Metrics and KPIs

```yaml
security_metrics:
  vulnerability_metrics:
    - critical_vulnerabilities: target=0, threshold=0
    - high_vulnerabilities: target=<5, threshold=10
    - mean_time_to_fix: target=<7d, threshold=14d
    - vulnerability_trends: tracking=monthly
    
  code_quality_metrics:
    - security_issues_per_kloc: target=<1, threshold=3
    - test_coverage: target=>90%, threshold=80%
    - dependency_freshness: target=<30d, threshold=90d
    
  process_metrics:
    - security_scan_coverage: target=100%, threshold=95%
    - false_positive_rate: target=<10%, threshold=20%
    - security_review_time: target=<24h, threshold=48h
```

## Related Decisions
- ADR-0001: Project Architecture Framework
- ADR-0002: Attack Pattern Plugin System
- ADR-0004: Monitoring and Observability Stack
- ADR-0005: Testing Strategy and Framework

## References
- [OWASP DevSecOps Guideline](https://owasp.org/www-project-devsecops-guideline/)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/Projects/ssdf)
- [SARIF Standard Documentation](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Security Tool Comparison Matrix](https://github.com/analysis-tools-dev/static-analysis)
- [Software Bill of Materials (SBOM) Guide](https://www.cisa.gov/sbom)