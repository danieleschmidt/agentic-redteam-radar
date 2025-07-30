# Release Automation Framework

This document outlines the automated release process for Agentic RedTeam Radar, including version management, changelog generation, and deployment automation.

## Release Strategy

### Semantic Versioning
We follow [Semantic Versioning](https://semver.org/) (SemVer):
- **MAJOR**: Breaking changes to public API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Channels
- **Stable** (`main`): Production-ready releases
- **Beta** (`develop`): Feature-complete pre-releases
- **Alpha** (`feature/*`): Development snapshots

## Automated Release Process

### 1. Version Detection
The release system automatically determines version increments based on:
- Commit message conventions (Conventional Commits)
- Pull request labels
- Breaking change indicators

```yaml
# Conventional Commit Examples
feat: add new attack pattern detection        # MINOR
fix: resolve memory leak in scanner          # PATCH  
feat!: restructure API for better security   # MAJOR
```

### 2. Changelog Generation
Automated changelog generation from commit history:

```markdown
## [1.2.0] - 2025-01-30

### Added
- New prompt injection detection patterns
- Multi-agent testing capabilities
- Performance benchmarking framework

### Changed
- Improved error handling in scanner core
- Updated dependencies for security patches

### Fixed
- Memory leak in long-running scans
- Race condition in parallel test execution

### Security
- Enhanced input validation
- Upgraded vulnerable dependencies
```

### 3. Release Artifacts
Each release automatically generates:

```
agentic-redteam-radar-1.2.0/
├── dist/
│   ├── agentic_redteam_radar-1.2.0.tar.gz
│   └── agentic_redteam_radar-1.2.0-py3-none-any.whl
├── docker/
│   ├── terragon/agentic-redteam-radar:1.2.0
│   ├── terragon/agentic-redteam-radar:1.2.0-slim
│   └── terragon/agentic-redteam-radar:latest
└── docs/
    ├── CHANGELOG.md
    ├── MIGRATION_GUIDE.md
    └── API_REFERENCE.md
```

## GitHub Actions Workflow Template

Since GitHub Actions workflows cannot be directly created, here's the template to implement:

### `.github/workflows/release.yml`

```yaml
name: Automated Release

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      version_increment:
        description: 'Version increment type'
        required: true
        default: 'patch'
        type: choice
        options:
        - patch
        - minor
        - major
      release_notes:
        description: 'Additional release notes'
        required: false

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      should-release: ${{ steps.changes.outputs.should-release }}
      version-increment: ${{ steps.changes.outputs.version-increment }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Detect Version Increment
        id: changes
        run: |
          # Analyze commits since last release
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
          COMMITS=$(git log ${LAST_TAG}..HEAD --oneline)
          
          if echo "$COMMITS" | grep -q "BREAKING CHANGE\|!:"; then
            echo "version-increment=major" >> $GITHUB_OUTPUT
          elif echo "$COMMITS" | grep -q "^feat"; then
            echo "version-increment=minor" >> $GITHUB_OUTPUT  
          else
            echo "version-increment=patch" >> $GITHUB_OUTPUT
          fi
          
          if [ -n "$COMMITS" ]; then
            echo "should-release=true" >> $GITHUB_OUTPUT
          else
            echo "should-release=false" >> $GITHUB_OUTPUT
          fi

  create-release:
    needs: detect-changes
    if: needs.detect-changes.outputs.should-release == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.RELEASE_TOKEN }}
          
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install Release Tools
        run: |
          pip install build twine bump2version gitpython
          
      - name: Configure Git
        run: |
          git config user.name "release-bot"
          git config user.email "release@terragonlabs.com"
          
      - name: Bump Version
        run: |
          VERSION_INCREMENT=${{ github.event.inputs.version_increment || needs.detect-changes.outputs.version-increment }}
          bump2version ${VERSION_INCREMENT}
          
      - name: Generate Changelog
        run: |
          python scripts/generate_changelog.py
          
      - name: Build Package
        run: |
          python -m build
          
      - name: Run Security Scan
        run: |
          pip install bandit pip-audit
          bandit -r src/
          pip-audit --requirement requirements.txt
          
      - name: Run Tests
        run: |
          pip install tox
          tox -e py310,security
          
      - name: Create Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          VERSION=$(python -c "import src.agentic_redteam; print(src.agentic_redteam.__version__)")
          
          gh release create "v${VERSION}" \
            --title "Release v${VERSION}" \
            --notes-file CHANGELOG_LATEST.md \
            --generate-notes \
            dist/*
            
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          twine upload dist/*
          
      - name: Build and Push Docker Images
        run: |
          VERSION=$(python -c "import src.agentic_redteam; print(src.agentic_redteam.__version__)")
          
          docker build -t terragon/agentic-redteam-radar:${VERSION} .
          docker build -t terragon/agentic-redteam-radar:${VERSION}-slim -f Dockerfile.slim .
          docker tag terragon/agentic-redteam-radar:${VERSION} terragon/agentic-redteam-radar:latest
          
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push terragon/agentic-redteam-radar:${VERSION}
          docker push terragon/agentic-redteam-radar:${VERSION}-slim
          docker push terragon/agentic-redteam-radar:latest
```

## Release Scripts

### Version Bump Script
```python
# scripts/bump_version.py
import re
import sys
from pathlib import Path

def bump_version(increment_type):
    """Bump version in pyproject.toml and __init__.py"""
    pyproject_path = Path("pyproject.toml")
    init_path = Path("src/agentic_redteam/__init__.py")
    
    # Read current version
    content = pyproject_path.read_text()
    version_match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', content)
    
    if not version_match:
        raise ValueError("Version not found in pyproject.toml")
    
    major, minor, patch = map(int, version_match.groups())
    
    # Increment based on type
    if increment_type == "major":
        major += 1
        minor = 0  
        patch = 0
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid increment type: {increment_type}")
    
    new_version = f"{major}.{minor}.{patch}"
    
    # Update pyproject.toml
    new_content = re.sub(
        r'version = "\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content
    )
    pyproject_path.write_text(new_content)
    
    # Update __init__.py
    init_content = f'__version__ = "{new_version}"\n'
    init_path.write_text(init_content)
    
    return new_version
```

### Changelog Generator
```python
# scripts/generate_changelog.py
import subprocess
import re
from datetime import datetime
from pathlib import Path

def generate_changelog():
    """Generate changelog from git commits"""
    # Get commits since last tag
    try:
        last_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        last_tag = None
    
    # Get commit range
    if last_tag:
        commit_range = f"{last_tag}..HEAD"
    else:
        commit_range = "HEAD"
    
    # Get commits
    commits = subprocess.check_output([
        "git", "log", commit_range,
        "--pretty=format:%s (%h)"
    ]).decode().strip().split('\n')
    
    # Categorize commits
    categories = {
        'Added': [],
        'Changed': [],
        'Fixed': [],
        'Security': [],
        'Breaking': []
    }
    
    for commit in commits:
        if commit.startswith('feat!') or 'BREAKING CHANGE' in commit:
            categories['Breaking'].append(commit)
        elif commit.startswith('feat'):
            categories['Added'].append(commit)
        elif commit.startswith('fix'):
            categories['Fixed'].append(commit)
        elif commit.startswith('sec') or 'security' in commit.lower():
            categories['Security'].append(commit)
        else:
            categories['Changed'].append(commit)
    
    # Generate changelog section
    version = get_current_version()
    date = datetime.now().strftime('%Y-%m-%d')
    
    changelog = [f"## [{version}] - {date}\n"]
    
    for category, items in categories.items():
        if items:
            changelog.append(f"### {category}")
            for item in items:
                changelog.append(f"- {item}")
            changelog.append("")
    
    # Write to files
    changelog_text = '\n'.join(changelog)
    
    # Update main CHANGELOG.md
    existing_changelog = Path("CHANGELOG.md").read_text()
    new_changelog = changelog_text + "\n" + existing_changelog
    Path("CHANGELOG.md").write_text(new_changelog)
    
    # Create latest changelog for release notes
    Path("CHANGELOG_LATEST.md").write_text(changelog_text)
```

## Release Checklist

### Pre-Release (Automated)
- [ ] All CI checks pass
- [ ] Security scans complete
- [ ] Performance tests pass
- [ ] Documentation updated
- [ ] Version bumped correctly

### Release (Automated)
- [ ] Git tag created
- [ ] GitHub release created
- [ ] PyPI package published
- [ ] Docker images built and pushed
- [ ] Changelog generated
- [ ] Release notes published

### Post-Release (Manual)
- [ ] Verify package installation
- [ ] Test Docker images
- [ ] Update documentation site
- [ ] Announce on social media
- [ ] Update dependent projects

## Rollback Procedures

### PyPI Package Rollback
```bash
# Yank problematic version (doesn't delete, just hides)
twine upload --repository-url https://upload.pypi.org/legacy/ \
  --username __token__ --password $PYPI_TOKEN \
  --comment "Critical security issue" \
  --yank

# Create hotfix release
git checkout main
git checkout -b hotfix/1.2.1
# Apply fixes
# Follow normal release process
```

### Docker Image Rollback
```bash
# Retag previous stable version as latest
docker tag terragon/agentic-redteam-radar:1.1.0 terragon/agentic-redteam-radar:latest
docker push terragon/agentic-redteam-radar:latest

# Update release notes with rollback information
gh release edit v1.2.0 --notes "**ROLLED BACK** - Critical issue found. Use v1.1.0 instead."
```

## Monitoring & Alerts

### Release Health Metrics
- Download/installation success rates
- User feedback and issue reports
- Performance regression detection
- Security scan results

### Automated Alerts
```yaml
# Slack notification template
- name: Notify Release
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,commit,author,action,eventName,ref,workflow
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

## Documentation Updates

All release documentation is automatically updated:
- API Reference
- Migration guides for breaking changes
- Installation instructions
- Docker image tags
- Version compatibility matrix

This automated release framework ensures consistent, secure, and reliable software delivery while maintaining high quality standards.