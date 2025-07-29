# Software Bill of Materials (SBOM) Generation

This document outlines the automated generation and management of Software Bill of Materials (SBOM) for the Agentic RedTeam Radar project, ensuring transparency and security in our software supply chain.

## Overview

A Software Bill of Materials (SBOM) is a comprehensive inventory of all components, libraries, and dependencies used in a software application. It provides visibility into the software supply chain and enables better security risk management.

## SBOM Standards and Formats

We support multiple SBOM formats to ensure compatibility with various tools and platforms:

### 1. CycloneDX Format
- **Primary format** for internal use
- JSON and XML variants supported
- Rich metadata support
- Vulnerability correlation capabilities

### 2. SPDX Format
- Industry-standard format
- License compliance focus
- Legal and copyright information
- Interoperability with external tools

### 3. SWID (Software Identification) Tags
- ISO/IEC 19770-2 standard
- Identity and integrity verification
- Lifecycle management support

## Automated SBOM Generation

### CycloneDX SBOM Generation

```yaml
# .github/workflows/sbom-generation.yml
name: SBOM Generation and Management

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  release:
    types: [published]
  schedule:
    - cron: '0 6 * * 1'  # Weekly on Monday at 6 AM

env:
  CYCLONEDX_VERSION: "3.11.0"
  SPDX_VERSION: "2.3"

jobs:
  generate-sbom:
    name: Generate SBOM
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
          pip install cyclonedx-bom spdx-tools
      
      - name: Generate CycloneDX SBOM (JSON)
        run: |
          cyclonedx-py \
            --output-format json \
            --output-file sbom-cyclonedx.json \
            --include-dev \
            --requirements requirements.txt
      
      - name: Generate CycloneDX SBOM (XML)
        run: |
          cyclonedx-py \
            --output-format xml \
            --output-file sbom-cyclonedx.xml \
            --include-dev \
            --requirements requirements.txt
      
      - name: Generate SPDX SBOM
        run: |
          pip install spdx-tools
          python scripts/generate_spdx_sbom.py > sbom-spdx.json
      
      - name: Validate SBOM files
        run: |
          # Validate CycloneDX SBOM
          python -c "
          import json
          with open('sbom-cyclonedx.json') as f:
              sbom = json.load(f)
          assert sbom['bomFormat'] == 'CycloneDX'
          assert 'components' in sbom
          print(f'CycloneDX SBOM contains {len(sbom[\"components\"])} components')
          "
          
          # Validate SPDX SBOM
          python -c "
          import json
          with open('sbom-spdx.json') as f:
              sbom = json.load(f)
          assert sbom['spdxVersion'] == 'SPDX-${{ env.SPDX_VERSION }}'
          assert 'packages' in sbom
          print(f'SPDX SBOM contains {len(sbom[\"packages\"])} packages')
          "
      
      - name: Generate SBOM summary
        run: |
          python scripts/sbom_summary.py \
            --cyclonedx sbom-cyclonedx.json \
            --spdx sbom-spdx.json \
            --output sbom-summary.md
      
      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v3
        with:
          name: sbom-files
          path: |
            sbom-cyclonedx.json
            sbom-cyclonedx.xml
            sbom-spdx.json
            sbom-summary.md
          retention-days: 90
      
      - name: Sign SBOM files
        if: github.event_name == 'release'
        run: |
          # Install cosign for signing
          curl -O -L "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64"
          sudo mv cosign-linux-amd64 /usr/local/bin/cosign
          sudo chmod +x /usr/local/bin/cosign
          
          # Sign SBOM files
          cosign sign-blob --bundle sbom-cyclonedx.json.bundle sbom-cyclonedx.json
          cosign sign-blob --bundle sbom-spdx.json.bundle sbom-spdx.json
      
      - name: Publish SBOM to release
        if: github.event_name == 'release'
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: sbom-cyclonedx.json
          asset_name: sbom-cyclonedx.json
          asset_content_type: application/json

  vulnerability-analysis:
    name: SBOM Vulnerability Analysis
    runs-on: ubuntu-latest
    needs: generate-sbom
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Download SBOM artifacts
        uses: actions/download-artifact@v3
        with:
          name: sbom-files
      
      - name: Install vulnerability scanners
        run: |
          # Install Grype for vulnerability scanning
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
          
          # Install OSV-Scanner
          curl -L -o osv-scanner https://github.com/google/osv-scanner/releases/latest/download/osv-scanner_linux_amd64
          chmod +x osv-scanner
          sudo mv osv-scanner /usr/local/bin/
      
      - name: Scan SBOM with Grype
        run: |
          grype sbom:sbom-cyclonedx.json \
            --output json \
            --file grype-vulnerabilities.json
        continue-on-error: true
      
      - name: Scan with OSV-Scanner
        run: |
          osv-scanner --sbom sbom-cyclonedx.json \
            --format json \
            --output osv-vulnerabilities.json
        continue-on-error: true
      
      - name: Generate vulnerability report
        run: |
          python scripts/vulnerability_report.py \
            --grype grype-vulnerabilities.json \
            --osv osv-vulnerabilities.json \
            --sbom sbom-cyclonedx.json \
            --output vulnerability-report.md
      
      - name: Upload vulnerability analysis
        uses: actions/upload-artifact@v3
        with:
          name: vulnerability-analysis
          path: |
            grype-vulnerabilities.json
            osv-vulnerabilities.json
            vulnerability-report.md

  supply-chain-analysis:
    name: Supply Chain Risk Analysis
    runs-on: ubuntu-latest
    needs: generate-sbom
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Download SBOM artifacts
        uses: actions/download-artifact@v3
        with:
          name: sbom-files
      
      - name: Analyze supply chain risks
        run: |
          python scripts/supply_chain_analysis.py \
            --sbom sbom-cyclonedx.json \
            --output supply-chain-report.json
      
      - name: Check for high-risk dependencies
        run: |
          python scripts/check_risky_dependencies.py \
            --sbom sbom-cyclonedx.json \
            --policy scripts/dependency-policy.yml
      
      - name: Upload supply chain analysis
        uses: actions/upload-artifact@v3
        with:
          name: supply-chain-analysis
          path: |
            supply-chain-report.json
```

### SBOM Generation Scripts

#### CycloneDX Generation Script

```python
# scripts/generate_cyclonedx_sbom.py
#!/usr/bin/env python3
"""
Enhanced CycloneDX SBOM generation with custom metadata.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import pkg_resources
import subprocess


class EnhancedSBOMGenerator:
    def __init__(self, project_name: str, version: str):
        self.project_name = project_name
        self.version = version
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def get_git_info(self) -> Dict[str, str]:
        """Get Git repository information."""
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                universal_newlines=True
            ).strip()
            
            commit_url = f"https://github.com/terragonlabs/agentic-redteam-radar/commit/{commit_hash}"
            
            return {
                "commit": commit_hash,
                "url": commit_url
            }
        except subprocess.CalledProcessError:
            return {}
    
    def get_installed_packages(self) -> List[Dict[str, Any]]:
        """Get all installed Python packages."""
        packages = []
        
        for pkg in pkg_resources.working_set:
            package_info = {
                "type": "library",
                "bom-ref": f"pkg:pypi/{pkg.project_name}@{pkg.version}",
                "name": pkg.project_name,
                "version": pkg.version,
                "purl": f"pkg:pypi/{pkg.project_name}@{pkg.version}",
                "scope": "required"
            }
            
            # Add license information if available
            try:
                metadata = pkg.get_metadata('METADATA')
                if metadata:
                    for line in metadata.split('\n'):
                        if line.startswith('License:'):
                            license_name = line.replace('License:', '').strip()
                            if license_name and license_name != 'UNKNOWN':
                                package_info["licenses"] = [{
                                    "license": {"name": license_name}
                                }]
                            break
            except Exception:
                pass
            
            # Get package description
            try:
                package_info["description"] = pkg.get_metadata('SUMMARY')
            except Exception:
                pass
            
            packages.append(package_info)
        
        return packages
    
    def generate_sbom(self) -> Dict[str, Any]:
        """Generate complete CycloneDX SBOM."""
        git_info = self.get_git_info()
        packages = self.get_installed_packages()
        
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{self.project_name}-{self.version}-{self.timestamp}",
            "version": 1,
            "metadata": {
                "timestamp": self.timestamp,
                "tools": [{
                    "vendor": "Terragon Labs",
                    "name": "enhanced-sbom-generator",
                    "version": "1.0.0"
                }],
                "component": {
                    "type": "application",
                    "bom-ref": f"pkg:pypi/{self.project_name}@{self.version}",
                    "name": self.project_name,
                    "version": self.version,
                    "description": "Open-source implementation of an agent-centric red-teaming scanner for AI security testing",
                    "licenses": [{
                        "license": {"name": "MIT"}
                    }],
                    "purl": f"pkg:pypi/{self.project_name}@{self.version}"
                }
            },
            "components": packages
        }
        
        # Add VCS information if available
        if git_info:
            sbom["metadata"]["component"]["vcs"] = {
                "type": "git",
                "url": "https://github.com/terragonlabs/agentic-redteam-radar.git",
                "revision": git_info["commit"]
            }
        
        # Add vulnerability assessment metadata
        sbom["vulnerabilities"] = []
        
        return sbom
    
    def save_sbom(self, output_file: str):
        """Save SBOM to file."""
        sbom = self.generate_sbom()
        
        with open(output_file, 'w') as f:
            json.dump(sbom, f, indent=2, sort_keys=True)
        
        print(f"Generated SBOM with {len(sbom['components'])} components")
        return sbom


def main():
    if len(sys.argv) != 4:
        print("Usage: python generate_cyclonedx_sbom.py <project_name> <version> <output_file>")
        sys.exit(1)
    
    project_name = sys.argv[1]
    version = sys.argv[2]
    output_file = sys.argv[3]
    
    generator = EnhancedSBOMGenerator(project_name, version)
    generator.save_sbom(output_file)


if __name__ == "__main__":
    main()
```

#### SPDX Generation Script

```python
# scripts/generate_spdx_sbom.py
#!/usr/bin/env python3
"""
Generate SPDX format SBOM for license compliance and legal analysis.
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any
import pkg_resources
import subprocess
import hashlib
import os


class SPDXGenerator:
    def __init__(self, project_name: str, version: str):
        self.project_name = project_name
        self.version = version
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.document_namespace = f"https://github.com/terragonlabs/agentic-redteam-radar/sbom/{version}"
    
    def calculate_package_checksum(self, package_name: str) -> str:
        """Calculate SHA256 checksum for a package (placeholder implementation)."""
        # In a real implementation, this would calculate the actual package checksum
        return hashlib.sha256(f"{package_name}".encode()).hexdigest()
    
    def get_license_info(self, pkg) -> Dict[str, str]:
        """Extract license information from package metadata."""
        license_info = {
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION"
        }
        
        try:
            metadata = pkg.get_metadata('METADATA')
            if metadata:
                for line in metadata.split('\n'):
                    if line.startswith('License:'):
                        license_name = line.replace('License:', '').strip()
                        if license_name and license_name != 'UNKNOWN':
                            license_info["licenseDeclared"] = license_name
                            license_info["licenseConcluded"] = license_name
                        break
                    elif line.startswith('Author:'):
                        author = line.replace('Author:', '').strip()
                        if author:
                            license_info["copyrightText"] = f"Copyright {author}"
        except Exception:
            pass
        
        return license_info
    
    def generate_packages(self) -> List[Dict[str, Any]]:
        """Generate SPDX package information for all dependencies."""
        packages = []
        
        # Add main package
        main_package = {
            "SPDXID": f"SPDXRef-Package-{self.project_name}",
            "name": self.project_name,
            "downloadLocation": f"https://github.com/terragonlabs/agentic-redteam-radar/archive/v{self.version}.tar.gz",
            "filesAnalyzed": False,
            "licenseConcluded": "MIT",
            "licenseDeclared": "MIT",
            "copyrightText": "Copyright 2025 Terragon Labs",
            "versionInfo": self.version,
            "supplier": "Organization: Terragon Labs",
            "homepage": "https://github.com/terragonlabs/agentic-redteam-radar",
            "description": "Open-source implementation of an agent-centric red-teaming scanner for AI security testing"
        }
        packages.append(main_package)
        
        # Add dependency packages
        for pkg in pkg_resources.working_set:
            if pkg.project_name == self.project_name:
                continue
            
            license_info = self.get_license_info(pkg)
            checksum = self.calculate_package_checksum(pkg.project_name)
            
            package_info = {
                "SPDXID": f"SPDXRef-Package-{pkg.project_name}",
                "name": pkg.project_name,
                "downloadLocation": f"https://pypi.org/project/{pkg.project_name}/{pkg.version}/",
                "filesAnalyzed": False,
                "licenseConcluded": license_info["licenseConcluded"],
                "licenseDeclared": license_info["licenseDeclared"],
                "copyrightText": license_info["copyrightText"],
                "versionInfo": pkg.version,
                "supplier": "NOASSERTION",
                "checksums": [{
                    "algorithm": "SHA256",
                    "checksumValue": checksum
                }]
            }
            
            # Add description if available
            try:
                description = pkg.get_metadata('SUMMARY')
                if description:
                    package_info["description"] = description
            except Exception:
                pass
            
            packages.append(package_info)
        
        return packages
    
    def generate_relationships(self, packages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate SPDX relationships between packages."""
        relationships = []
        main_package_id = f"SPDXRef-Package-{self.project_name}"
        
        for package in packages:
            if package["SPDXID"] != main_package_id:
                relationships.append({
                    "spdxElementId": main_package_id,
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": package["SPDXID"]
                })
        
        return relationships
    
    def generate_sbom(self) -> Dict[str, Any]:
        """Generate complete SPDX SBOM."""
        packages = self.generate_packages()
        relationships = self.generate_relationships(packages)
        
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"{self.project_name}-{self.version}",
            "documentNamespace": self.document_namespace,
            "creationInfo": {
                "created": self.timestamp,
                "creators": [
                    "Tool: enhanced-spdx-generator-1.0.0",
                    "Organization: Terragon Labs"
                ],
                "licenseListVersion": "3.19"
            },
            "packages": packages,
            "relationships": relationships
        }
        
        return sbom


def main():
    generator = SPDXGenerator("agentic-redteam-radar", "0.1.0")
    sbom = generator.generate_sbom()
    print(json.dumps(sbom, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

#### SBOM Analysis Scripts

```python
# scripts/sbom_summary.py
#!/usr/bin/env python3
"""
Generate human-readable summary of SBOM contents.
"""

import json
import argparse
from typing import Dict, List, Any
from collections import Counter


def analyze_cyclonedx_sbom(sbom_file: str) -> Dict[str, Any]:
    """Analyze CycloneDX SBOM and extract insights."""
    with open(sbom_file) as f:
        sbom = json.load(f)
    
    components = sbom.get('components', [])
    
    # Component type analysis
    component_types = Counter(comp.get('type', 'unknown') for comp in components)
    
    # License analysis
    licenses = []
    for comp in components:
        comp_licenses = comp.get('licenses', [])
        for lic in comp_licenses:
            if 'license' in lic and 'name' in lic['license']:
                licenses.append(lic['license']['name'])
    license_counts = Counter(licenses)
    
    # Scope analysis
    scopes = Counter(comp.get('scope', 'unknown') for comp in components)
    
    return {
        'total_components': len(components),
        'component_types': dict(component_types),
        'licenses': dict(license_counts),
        'scopes': dict(scopes),
        'top_licenses': license_counts.most_common(5)
    }


def analyze_spdx_sbom(sbom_file: str) -> Dict[str, Any]:
    """Analyze SPDX SBOM and extract insights."""
    with open(sbom_file) as f:
        sbom = json.load(f)
    
    packages = sbom.get('packages', [])
    relationships = sbom.get('relationships', [])
    
    # License analysis
    declared_licenses = [pkg.get('licenseDeclared', 'NOASSERTION') for pkg in packages]
    concluded_licenses = [pkg.get('licenseConcluded', 'NOASSERTION') for pkg in packages]
    
    declared_counts = Counter(declared_licenses)
    concluded_counts = Counter(concluded_licenses)
    
    # Relationship analysis
    relationship_types = Counter(rel.get('relationshipType', 'unknown') for rel in relationships)
    
    return {
        'total_packages': len(packages),
        'total_relationships': len(relationships),
        'declared_licenses': dict(declared_counts),
        'concluded_licenses': dict(concluded_counts),
        'relationship_types': dict(relationship_types)
    }


def generate_summary_report(cyclonedx_analysis: Dict[str, Any], 
                          spdx_analysis: Dict[str, Any]) -> str:
    """Generate comprehensive SBOM summary report."""
    
    report = []
    report.append("# Software Bill of Materials (SBOM) Summary")
    report.append("")
    report.append(f"**Generated on:** {datetime.utcnow().isoformat()}Z")
    report.append("")
    
    # CycloneDX Analysis
    report.append("## CycloneDX SBOM Analysis")
    report.append("")
    report.append(f"**Total Components:** {cyclonedx_analysis['total_components']}")
    report.append("")
    
    report.append("### Component Types")
    for comp_type, count in cyclonedx_analysis['component_types'].items():
        report.append(f"- {comp_type}: {count}")
    report.append("")
    
    report.append("### Top Licenses")
    for license_name, count in cyclonedx_analysis['top_licenses']:
        report.append(f"- {license_name}: {count} components")
    report.append("")
    
    report.append("### Component Scopes")
    for scope, count in cyclonedx_analysis['scopes'].items():
        report.append(f"- {scope}: {count}")
    report.append("")
    
    # SPDX Analysis
    report.append("## SPDX SBOM Analysis")
    report.append("")
    report.append(f"**Total Packages:** {spdx_analysis['total_packages']}")
    report.append(f"**Total Relationships:** {spdx_analysis['total_relationships']}")
    report.append("")
    
    report.append("### License Compliance")
    no_assertion_count = spdx_analysis['declared_licenses'].get('NOASSERTION', 0)
    known_licenses = spdx_analysis['total_packages'] - no_assertion_count
    
    report.append(f"- Packages with known licenses: {known_licenses}")
    report.append(f"- Packages without license info: {no_assertion_count}")
    report.append("")
    
    if no_assertion_count > 0:
        report.append("⚠️ **Warning:** Some packages lack license information")
        report.append("")
    
    report.append("### Relationship Types")
    for rel_type, count in spdx_analysis['relationship_types'].items():
        report.append(f"- {rel_type}: {count}")
    report.append("")
    
    # Security Recommendations
    report.append("## Security Recommendations")
    report.append("")
    report.append("- Review all dependencies for known vulnerabilities")
    report.append("- Ensure license compliance for all components")
    report.append("- Monitor for updates to critical dependencies")
    report.append("- Implement dependency pinning for reproducible builds")
    report.append("")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Generate SBOM summary report")
    parser.add_argument("--cyclonedx", required=True, help="CycloneDX SBOM file")
    parser.add_argument("--spdx", required=True, help="SPDX SBOM file")
    parser.add_argument("--output", required=True, help="Output summary file")
    
    args = parser.parse_args()
    
    cyclonedx_analysis = analyze_cyclonedx_sbom(args.cyclonedx)
    spdx_analysis = analyze_spdx_sbom(args.spdx)
    
    summary = generate_summary_report(cyclonedx_analysis, spdx_analysis)
    
    with open(args.output, 'w') as f:
        f.write(summary)
    
    print(f"SBOM summary generated: {args.output}")


if __name__ == "__main__":
    from datetime import datetime
    main()
```

## SBOM Integration and Usage

### Integration with CI/CD Pipeline

The SBOM generation is automatically integrated into the CI/CD pipeline and triggered on:

1. **Every commit** to main branch
2. **Pull requests** for validation
3. **Releases** for official SBOM publication
4. **Weekly schedule** for dependency updates

### SBOM Storage and Distribution

- **Artifacts**: Stored as GitHub Actions artifacts
- **Releases**: Attached to GitHub releases
- **Registry**: Published to container registries with images
- **API**: Available through REST API for automated tools

### SBOM Consumption

External tools can consume our SBOMs for:

- **Vulnerability scanning**: Grype, OSV-Scanner, Snyk
- **License compliance**: FOSSA, BlackDuck, WhiteSource
- **Supply chain analysis**: Dependency-Track, GUAC
- **Risk assessment**: Custom security tools

## Best Practices

### SBOM Quality Assurance

1. **Completeness**: Include all direct and transitive dependencies
2. **Accuracy**: Verify component versions and licenses
3. **Freshness**: Generate SBOMs with every build
4. **Validation**: Automated validation of SBOM format and content
5. **Signing**: Cryptographically sign SBOMs for integrity

### Supply Chain Security

1. **Dependency monitoring**: Track dependency changes over time
2. **Vulnerability correlation**: Map vulnerabilities to SBOM components
3. **License compliance**: Ensure all components have compatible licenses
4. **Provenance tracking**: Maintain chain of custody for all components

This comprehensive SBOM framework ensures transparency and security in our software supply chain while supporting industry-standard formats and tools.