# Contributing to Agentic RedTeam Radar

Thank you for your interest in contributing to Agentic RedTeam Radar! This project helps improve AI agent security through responsible security testing.

## 🎯 Project Focus

This project is dedicated to **defensive security research** - helping developers identify and fix vulnerabilities in AI agents. All contributions must align with responsible disclosure and defensive security practices.

## 🤝 Ways to Contribute

### Priority Areas
- **Attack Patterns**: New defensive testing patterns for agent vulnerabilities
- **Framework Integrations**: Support for additional agent frameworks
- **Documentation**: Improving guides, examples, and API documentation
- **Bug Fixes**: Resolving issues and improving reliability
- **Performance**: Optimizing scanning speed and accuracy

### What We Need
- Security researchers with AI/ML experience
- Python developers familiar with async programming
- Technical writers for documentation
- DevOps engineers for CI/CD improvements

## 🚀 Getting Started

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/agentic-redteam-radar.git
   cd agentic-redteam-radar
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

4. **Run Tests**
   ```bash
   pytest
   ```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run tests
   pytest

   # Check code quality
   black .
   isort .
   flake8
   mypy src/
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new attack pattern for prompt injection"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Use descriptive title and clear description
   - Reference any related issues
   - Include testing instructions

## 📝 Coding Standards

### Code Style
- **Formatter**: Black (line length: 88)
- **Import sorting**: isort
- **Linting**: flake8
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style for all public functions

### Testing Requirements
- **Unit tests**: Required for all new functionality
- **Integration tests**: For complex attack patterns
- **Type checking**: All code must pass mypy
- **Coverage**: Maintain >90% test coverage

### Security Guidelines
- **No hardcoded secrets**: Use environment variables
- **Secure defaults**: All configurations should be secure by default
- **Input validation**: Validate all external inputs
- **Logging**: No sensitive data in logs

## 🧪 Adding Attack Patterns

New attack patterns should follow this structure:

```python
from agentic_redteam.attacks.base import AttackPattern
from agentic_redteam.models import AttackResult

class YourAttackPattern(AttackPattern):
    """
    Brief description of the attack pattern.
    
    This attack tests for [specific vulnerability] by [method].
    Reference: [relevant security research/CVE if applicable]
    """
    
    name = "your_attack_name"
    category = "prompt_injection"  # or info_disclosure, policy_bypass, etc.
    severity = "medium"  # low, medium, high, critical
    
    async def generate_payloads(self, target_agent):
        """Generate attack payloads for the target agent."""
        return [
            "payload 1",
            "payload 2"
        ]
    
    async def evaluate_response(self, payload, response):
        """Evaluate if the attack was successful."""
        return AttackResult(
            success=self._detect_vulnerability(response),
            confidence=0.85,
            evidence=response.content
        )
```

## 📋 Pull Request Guidelines

### Before Submitting
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Security impact assessed

### PR Description Template
```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Security improvement
- [ ] Performance optimization

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Security Impact
- [ ] No security implications
- [ ] Improves security posture
- [ ] Adds new attack detection capability

## Breaking Changes
- [ ] No breaking changes
- [ ] Breaking changes (describe below)
```

## 🔒 Security Considerations

### Responsible Disclosure
- Report vulnerabilities privately first
- Allow reasonable time for fixes
- Coordinate public disclosure responsibly

### Attack Pattern Guidelines
- Focus on defensive testing capabilities
- Provide clear remediation guidance
- Include references to security research
- Test against multiple agent types

### Code Security
- Review all dependencies for vulnerabilities
- Use security linters (bandit, safety)
- Follow OWASP secure coding practices
- Implement proper error handling

## 📖 Documentation

### Required Documentation
- **API Documentation**: All public functions and classes
- **Examples**: Practical usage examples
- **Security Guidance**: How to use features securely
- **Architecture**: High-level system design

### Documentation Style
- Clear, concise explanations
- Code examples that work
- Security warnings where appropriate
- Links to external resources

## 🧪 Testing

### Test Categories
- **Unit Tests**: Test individual functions
- **Integration Tests**: Test component interactions
- **Security Tests**: Test attack pattern effectiveness
- **Performance Tests**: Ensure acceptable performance

### Test Requirements
- All new code must have tests
- Tests should be deterministic
- Use mocking for external dependencies
- Include both positive and negative test cases

## 🚨 Issue Reporting

### Bug Reports
Use the bug report template and include:
- Python version and OS
- Full error traceback
- Minimal reproduction example
- Expected vs actual behavior

### Feature Requests
Use the feature request template and include:
- Clear problem description
- Proposed solution
- Alternative solutions considered
- Security implications

### Security Issues
- **DO NOT** open public issues for security vulnerabilities
- Email security@terragonlabs.com
- Include detailed reproduction steps
- Provide impact assessment

## 📜 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

## 🤔 Questions?

- **Documentation**: Check the [docs](https://agentic-redteam.readthedocs.io)
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Contact security@terragonlabs.com
- **General**: Open an issue with the "question" label

## 🙏 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Project documentation
- Conference presentations (with permission)

Thank you for helping make AI agents more secure! 🛡️