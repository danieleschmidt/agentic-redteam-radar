"""
HTML report generator for scan results.

Creates comprehensive HTML reports with interactive charts and detailed findings.
"""

import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from jinja2 import Template

from ..results import ScanResult


@dataclass
class HTMLReportConfig:
    """Configuration for HTML report generation."""
    title: str = "Agentic RedTeam Radar - Security Scan Report"
    include_charts: bool = True
    include_detailed_evidence: bool = True
    theme: str = "light"  # light, dark
    company_logo: Optional[str] = None


def generate_html_report(scan_result: ScanResult, config: Optional[HTMLReportConfig] = None) -> str:
    """
    Generate HTML report from scan results.
    
    Args:
        scan_result: Results from security scan
        config: HTML report configuration
        
    Returns:
        HTML content as string
    """
    if not config:
        config = HTMLReportConfig()
    
    # Prepare data for template
    report_data = {
        'config': config,
        'scan_result': scan_result,
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'severity_counts': _get_severity_counts(scan_result),
        'category_counts': _get_category_counts(scan_result),
        'risk_score': _calculate_risk_score(scan_result),
        'severity_colors': {
            'critical': '#dc3545',
            'high': '#fd7e14', 
            'medium': '#ffc107',
            'low': '#28a745',
            'info': '#17a2b8'
        }
    }
    
    # HTML template
    html_template = _get_html_template()
    
    # Render template
    template = Template(html_template)
    return template.render(**report_data)


def _get_severity_counts(scan_result: ScanResult) -> Dict[str, int]:
    """Count vulnerabilities by severity."""
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    
    for vuln in scan_result.vulnerabilities:
        severity = vuln.severity.lower() if hasattr(vuln, 'severity') else 'info'
        if severity in counts:
            counts[severity] += 1
    
    return counts


def _get_category_counts(scan_result: ScanResult) -> Dict[str, int]:
    """Count vulnerabilities by category."""
    counts = {}
    
    for vuln in scan_result.vulnerabilities:
        category = vuln.category if hasattr(vuln, 'category') else 'other'
        counts[category] = counts.get(category, 0) + 1
    
    return counts


def _calculate_risk_score(scan_result: ScanResult) -> float:
    """Calculate overall risk score from 0-10."""
    if not scan_result.vulnerabilities:
        return 0.0
    
    severity_weights = {
        'critical': 4.0,
        'high': 3.0,
        'medium': 2.0, 
        'low': 1.0,
        'info': 0.1
    }
    
    total_score = 0.0
    for vuln in scan_result.vulnerabilities:
        severity = vuln.severity.lower() if hasattr(vuln, 'severity') else 'info'
        total_score += severity_weights.get(severity, 0.1)
    
    # Normalize to 0-10 scale
    max_possible = len(scan_result.vulnerabilities) * 4.0
    return min(10.0, (total_score / max_possible) * 10.0) if max_possible > 0 else 0.0


def _get_html_template() -> str:
    """Get HTML template for report generation."""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: {% if config.theme == 'dark' %}#1a1a1a{% else %}#f8f9fa{% endif %};
            color: {% if config.theme == 'dark' %}#ffffff{% else %}#333333{% endif %};
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: {% if config.theme == 'dark' %}#2d2d2d{% else %}white{% endif %};
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 0;
            opacity: 0.9;
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .card {
            background: {% if config.theme == 'dark' %}#3d3d3d{% else %}#f8f9fa{% endif %};
            padding: 20px;
            border-radius: 8px;
            border: 1px solid {% if config.theme == 'dark' %}#555{% else %}#dee2e6{% endif %};
        }
        .card h3 {
            margin: 0 0 10px 0;
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .card .value {
            font-size: 2em;
            font-weight: bold;
            margin: 0;
        }
        .risk-score {
            color: {% if risk_score >= 7 %}#dc3545{% elif risk_score >= 4 %}#ffc107{% else %}#28a745{% endif %};
        }
        .charts-section {
            padding: 30px;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }
        .chart-container {
            background: {% if config.theme == 'dark' %}#3d3d3d{% else %}white{% endif %};
            padding: 20px;
            border-radius: 8px;
            border: 1px solid {% if config.theme == 'dark' %}#555{% else %}#dee2e6{% endif %};
        }
        .vulnerabilities-table {
            padding: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid {% if config.theme == 'dark' %}#555{% else %}#dee2e6{% endif %};
        }
        th {
            background-color: {% if config.theme == 'dark' %}#3d3d3d{% else %}#f8f9fa{% endif %};
            font-weight: 600;
        }
        .severity {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        .severity-critical { background-color: #dc3545; }
        .severity-high { background-color: #fd7e14; }
        .severity-medium { background-color: #ffc107; color: #333; }
        .severity-low { background-color: #28a745; }
        .severity-info { background-color: #17a2b8; }
        .footer {
            padding: 30px;
            text-align: center;
            background-color: {% if config.theme == 'dark' %}#2d2d2d{% else %}#f8f9fa{% endif %};
            color: #6c757d;
            border-top: 1px solid {% if config.theme == 'dark' %}#555{% else %}#dee2e6{% endif %};
        }
        .agent-info {
            background: {% if config.theme == 'dark' %}#3d3d3d{% else %}#e9ecef{% endif %};
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }
        .agent-info h3 {
            margin: 0 0 15px 0;
            color: {% if config.theme == 'dark' %}#ffffff{% else %}#495057{% endif %};
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
        }
        .info-label {
            font-weight: 600;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {% if config.company_logo %}
            <img src="{{ config.company_logo }}" alt="Logo" style="max-height: 50px; margin-bottom: 20px;">
            {% endif %}
            <h1>🎯 Security Scan Report</h1>
            <p>{{ config.title }}</p>
            <p>Generated on {{ generated_at }}</p>
        </div>

        <div class="summary-cards">
            <div class="card">
                <h3>Agent Tested</h3>
                <p class="value">{{ scan_result.agent_name }}</p>
            </div>
            <div class="card">
                <h3>Scan Duration</h3>
                <p class="value">{{ "%.2f"|format(scan_result.scan_duration) }}s</p>
            </div>
            <div class="card">
                <h3>Total Vulnerabilities</h3>
                <p class="value">{{ scan_result.vulnerabilities|length }}</p>
            </div>
            <div class="card">
                <h3>Risk Score</h3>
                <p class="value risk-score">{{ "%.1f"|format(risk_score) }}/10</p>
            </div>
        </div>

        <div class="agent-info">
            <h3>Agent Information</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Name:</span>
                    <span>{{ scan_result.agent_name }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Patterns Executed:</span>
                    <span>{{ scan_result.patterns_executed }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Total Tests:</span>
                    <span>{{ scan_result.total_tests }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Scanner Version:</span>
                    <span>{{ scan_result.scanner_version }}</span>
                </div>
            </div>
        </div>

        {% if config.include_charts and scan_result.vulnerabilities %}
        <div class="charts-section">
            <h2>Vulnerability Analysis</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>Vulnerabilities by Severity</h3>
                    <canvas id="severityChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Vulnerabilities by Category</h3>
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
        </div>
        {% endif %}

        {% if scan_result.vulnerabilities %}
        <div class="vulnerabilities-table">
            <h2>Detailed Vulnerability Report</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Category</th>
                        <th>Severity</th>
                        <th>Description</th>
                        {% if config.include_detailed_evidence %}
                        <th>Evidence</th>
                        {% endif %}
                    </tr>
                </thead>
                <tbody>
                    {% for vuln in scan_result.vulnerabilities %}
                    <tr>
                        <td>{{ vuln.name }}</td>
                        <td>{{ vuln.category }}</td>
                        <td>
                            <span class="severity severity-{{ vuln.severity.lower() }}">
                                {{ vuln.severity }}
                            </span>
                        </td>
                        <td>{{ vuln.description }}</td>
                        {% if config.include_detailed_evidence %}
                        <td>{{ vuln.evidence[:100] }}{% if vuln.evidence|length > 100 %}...{% endif %}</td>
                        {% endif %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="footer">
            <p>Report generated by Agentic RedTeam Radar v0.1.0</p>
            <p>🔒 This report contains sensitive security information - handle with care</p>
        </div>
    </div>

    {% if config.include_charts and scan_result.vulnerabilities %}
    <script>
        // Severity chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        new Chart(severityCtx, {
            type: 'doughnut',
            data: {
                labels: {{ severity_counts.keys()|list|tojson }},
                datasets: [{
                    data: {{ severity_counts.values()|list|tojson }},
                    backgroundColor: [
                        '{{ severity_colors.critical }}',
                        '{{ severity_colors.high }}',
                        '{{ severity_colors.medium }}', 
                        '{{ severity_colors.low }}',
                        '{{ severity_colors.info }}'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Category chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {
            type: 'bar',
            data: {
                labels: {{ category_counts.keys()|list|tojson }},
                datasets: [{
                    label: 'Vulnerabilities',
                    data: {{ category_counts.values()|list|tojson }},
                    backgroundColor: '{{ severity_colors.medium }}',
                    borderColor: '{{ severity_colors.high }}',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    </script>
    {% endif %}
</body>
</html>
    '''