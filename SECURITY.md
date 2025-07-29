# Security Policy

## Reporting Security Vulnerabilities

### For This Project
If you discover a security vulnerability in Agentic RedTeam Radar itself:

**DO NOT** create a public GitHub issue.

Instead, please email: security@terragonlabs.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested remediation (if known)

### For AI Agents Under Test
If you discover vulnerabilities in AI agents using this tool:

1. **DO NOT** exploit in production systems
2. Report to the agent vendor/developer privately first
3. Allow reasonable time for patches (typically 90 days)
4. Share sanitized attack patterns with our research team

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Features

### Built-in Protections
- API key management via environment variables
- Rate limiting for external service calls
- Input validation for all attack patterns
- Secure temporary file handling
- Audit logging for all security tests

### Recommendations
- Use isolated testing environments
- Regularly rotate API keys
- Monitor usage for anomalous patterns
- Keep dependencies updated
- Review attack patterns before deployment

## Responsible Disclosure

We follow responsible disclosure principles:
- Private reporting of vulnerabilities
- Reasonable response timeframes
- Coordinated public disclosure
- Credit to security researchers (with permission)

Response timeline:
- **24 hours**: Initial acknowledgment
- **7 days**: Vulnerability assessment
- **30 days**: Fix development (critical issues)
- **90 days**: Public disclosure coordination

## Security Resources

- [OWASP AI Security Guide](https://owasp.org/www-project-ai-security-and-privacy-guide/)
- [Cloud Security Alliance AI Guidelines](https://cloudsecurityalliance.org/research/working-groups/artificial-intelligence/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

## Contact

- **Security issues**: security@terragonlabs.com
- **General questions**: Use GitHub Discussions
- **PGP Key**: Available on request