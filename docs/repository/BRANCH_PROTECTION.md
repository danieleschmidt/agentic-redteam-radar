# Branch Protection Configuration

This document outlines the recommended branch protection rules for the Agentic RedTeam Radar repository to ensure code quality, security, and collaborative development standards.

## Branch Protection Rules

### Main Branch (`main`)

**Required Status Checks:**
- `ci/tests` - All test suites must pass
- `ci/security-scan` - Security scanning must pass
- `ci/lint` - Code quality checks must pass
- `ci/type-check` - Type checking must pass
- `dependabot/security-updates` - Security updates must be reviewed

**Pull Request Requirements:**
- Require pull request reviews before merging: **Yes**
- Required number of reviewers: **2**
- Dismiss stale reviews when new commits are pushed: **Yes**
- Require review from CODEOWNERS: **Yes**
- Restrict who can dismiss reviews: Core maintainers only

**Additional Restrictions:**
- Restrict pushes that create files or directories: **No**
- Require branches to be up to date before merging: **Yes**
- Require conversation resolution before merging: **Yes**
- Include administrators in restrictions: **Yes**
- Allow force pushes: **No**
- Allow deletions: **No**

### Development Branch (`develop`)

**Required Status Checks:**
- `ci/tests` - All test suites must pass
- `ci/security-scan` - Security scanning must pass
- `ci/lint` - Code quality checks must pass

**Pull Request Requirements:**
- Require pull request reviews before merging: **Yes**
- Required number of reviewers: **1**
- Require review from CODEOWNERS: **Yes**

**Additional Restrictions:**
- Require branches to be up to date before merging: **Yes**
- Allow force pushes: **No**
- Allow deletions: **No**

### Release Branches (`release/*`)

**Required Status Checks:**
- `ci/tests` - All test suites must pass
- `ci/security-scan` - Security scanning must pass
- `ci/integration-tests` - Integration tests must pass
- `ci/performance-tests` - Performance benchmarks must pass

**Pull Request Requirements:**
- Require pull request reviews before merging: **Yes**
- Required number of reviewers: **2**
- Require review from CODEOWNERS: **Yes**
- Restrict who can merge: Release managers only

## GitHub CLI Setup Commands

```bash
# Set up branch protection for main branch
gh api repos/terragonlabs/agentic-redteam-radar/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci/tests","ci/security-scan","ci/lint","ci/type-check"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true,"require_code_owner_reviews":true,"require_last_push_approval":true}' \
  --field restrictions=null

# Set up branch protection for develop branch  
gh api repos/terragonlabs/agentic-redteam-radar/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci/tests","ci/security-scan","ci/lint"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  --field restrictions=null
```

## Repository Settings

### General Settings
- Default branch: `main`
- Template repository: **No**
- Issues: **Enabled**
- Projects: **Enabled** 
- Wiki: **Disabled** (use docs/ instead)
- Discussions: **Enabled**

### Merge Settings
- Allow merge commits: **No**
- Allow squash merging: **Yes** (default)
- Allow rebase merging: **Yes**
- Always suggest updating pull request branches: **Yes**
- Automatically delete head branches: **Yes**

### Security Settings
- Dependency graph: **Enabled**
- Dependabot alerts: **Enabled**
- Dependabot security updates: **Enabled**
- Code scanning alerts: **Enabled**
- Secret scanning alerts: **Enabled**

### Access & Visibility
- Repository visibility: **Public**
- Restrict creation of public repositories: **No**
- Repository features: All enabled except Wiki

## Status Check Configuration

### Required Contexts

These status checks must pass before merging:

```json
{
  "ci/tests": {
    "description": "All test suites (unit, integration, performance)",
    "contexts": ["pytest", "tox"]
  },
  "ci/security-scan": {
    "description": "Security vulnerability scanning",
    "contexts": ["bandit", "pip-audit", "detect-secrets"]
  },
  "ci/lint": {
    "description": "Code quality and formatting",
    "contexts": ["black", "isort", "flake8", "mypy"]
  },
  "ci/type-check": {
    "description": "Static type checking",
    "contexts": ["mypy", "type-coverage"]
  }
}
```

### Optional Contexts

These provide additional quality signals but don't block merging:

```json
{
  "ci/docs": {
    "description": "Documentation build and validation"
  },
  "ci/coverage": {
    "description": "Code coverage reporting"
  },
  "ci/benchmark": {
    "description": "Performance regression testing"
  }
}
```

## Enforcement Timeline

1. **Phase 1 (Immediate)**: Enable basic protections
   - Require pull requests
   - Require 1 reviewer
   - Enable required status checks

2. **Phase 2 (Week 2)**: Strengthen requirements
   - Increase to 2 reviewers for main
   - Require CODEOWNERS review
   - Add security scanning requirements

3. **Phase 3 (Week 4)**: Full enforcement
   - Include administrators in restrictions
   - Enable all recommended status checks
   - Implement automated compliance monitoring

## Monitoring & Compliance

### Weekly Audits
- Review bypass events and justifications
- Monitor failed status checks patterns
- Assess review quality and coverage

### Monthly Reviews
- Update protection rules based on team growth
- Review and adjust required contexts
- Evaluate effectiveness of current rules

### Quarterly Assessments
- Comprehensive security review
- Team workflow optimization
- Rule refinement based on data

## Troubleshooting

### Common Issues

**Status checks not showing up:**
- Verify GitHub Actions workflow file syntax
- Check webhook delivery logs
- Ensure proper permissions are set

**Reviews not required from CODEOWNERS:**
- Verify CODEOWNERS file syntax
- Check file path matching patterns
- Confirm team membership and permissions

**Force push blocked:**
- This is intentional for protected branches
- Use pull requests for all changes
- Contact administrators for emergency overrides

### Emergency Procedures

For critical security patches requiring immediate deployment:

1. Create emergency branch from latest main
2. Request temporary protection bypass from repository admin
3. Apply fix with accelerated review process
4. Restore full protection immediately after merge
5. Document incident and improve prevention measures

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [CODEOWNERS Documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-status-checks)