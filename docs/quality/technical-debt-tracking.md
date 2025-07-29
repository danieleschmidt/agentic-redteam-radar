# Technical Debt Tracking and Code Quality Metrics

This document outlines the systematic approach to tracking technical debt, measuring code quality, and maintaining high standards throughout the Agentic RedTeam Radar project lifecycle.

## Overview

Technical debt represents the implied cost of additional rework caused by choosing an easy solution now instead of using a better approach that would take longer. This guide provides:

- **Technical Debt Classification**: Systematic categorization of debt types
- **Quality Metrics**: Quantitative measures of code quality
- **Tracking Systems**: Tools and processes for debt management
- **Remediation Strategies**: Approaches for addressing technical debt
- **Quality Gates**: Automated quality enforcement

## Technical Debt Classification

### Debt Categories

#### 1. Code Debt
**Definition**: Issues in the codebase that make it harder to maintain, extend, or understand.

**Examples:**
- Duplicated code across modules
- Complex functions with high cyclomatic complexity
- Poor naming conventions
- Missing or inadequate documentation
- Inconsistent coding styles

**Impact:** Increases development time, bug likelihood, and onboarding difficulty.

#### 2. Design Debt
**Definition**: Architectural decisions that create future constraints or maintenance burdens.

**Examples:**
- Tight coupling between components
- Violation of SOLID principles
- Inappropriate design patterns
- Lack of abstraction layers
- Monolithic components that should be modular

**Impact:** Reduces flexibility, increases change impact, limits scalability.

#### 3. Test Debt
**Definition**: Insufficient or poor-quality testing that reduces confidence in code changes.

**Examples:**
- Low test coverage
- Flaky or unreliable tests
- Missing integration tests
- Poor test organization
- Inadequate test data management

**Impact:** Increases bug escape rate, reduces deployment confidence, slows feature development.

#### 4. Documentation Debt
**Definition**: Missing, outdated, or inadequate documentation.

**Examples:**
- Outdated API documentation
- Missing architectural decision records
- Inadequate code comments
- No deployment guides
- Missing security documentation

**Impact:** Increases onboarding time, reduces team productivity, increases support burden.

#### 5. Infrastructure Debt
**Definition**: Outdated or suboptimal infrastructure, tooling, and processes.

**Examples:**
- Outdated dependencies
- Inefficient deployment processes
- Lack of automation
- Poor monitoring and alerting
- Inadequate security measures

**Impact:** Increases operational overhead, security risks, and development friction.

## Code Quality Metrics Framework

### Primary Quality Metrics

```yaml
# Quality metrics configuration
quality_metrics:
  code_quality:
    # Complexity metrics
    cyclomatic_complexity:
      target: < 10
      warning: 15
      critical: 20
      description: "Measure of code complexity based on decision points"
    
    cognitive_complexity:
      target: < 15
      warning: 25
      critical: 30
      description: "Measure of how difficult code is to understand"
    
    # Size metrics
    lines_of_code:
      target: < 100  # per function
      warning: 150
      critical: 200
      description: "Lines of code per function"
    
    # Duplication metrics
    code_duplication:
      target: < 3%
      warning: 5%
      critical: 10%
      description: "Percentage of duplicated code"
    
    # Maintainability metrics
    maintainability_index:
      target: > 80
      warning: 60
      critical: 40
      description: "Composite measure of maintainability (0-100)"
  
  test_quality:
    # Coverage metrics
    line_coverage:
      target: > 90%
      warning: 80%
      critical: 70%
      description: "Percentage of lines covered by tests"
    
    branch_coverage:
      target: > 85%
      warning: 75%
      critical: 65%
      description: "Percentage of branches covered by tests"
    
    mutation_score:
      target: > 80%
      warning: 70%
      critical: 60%
      description: "Percentage of mutations caught by tests"
  
  security_quality:
    # Security metrics
    security_hotspots:
      target: 0
      warning: 2
      critical: 5
      description: "Number of security hotspots identified"
    
    vulnerabilities:
      target: 0
      warning: 1
      critical: 3
      description: "Number of confirmed security vulnerabilities"

  dependency_quality:
    # Dependency metrics
    dependency_freshness:
      target: < 30  # days
      warning: 90
      critical: 180
      description: "Average age of dependencies"
    
    known_vulnerabilities:
      target: 0
      warning: 1
      critical: 3
      description: "Number of dependencies with known vulnerabilities"
```

### Quality Measurement Tools

#### Code Quality Analysis

```python
# scripts/code_quality_analyzer.py
"""
Comprehensive code quality analysis tool.
"""

import ast
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import re
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class QualityMetrics:
    """Code quality metrics data structure."""
    timestamp: str
    file_path: str
    lines_of_code: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: float
    duplication_ratio: float
    test_coverage: float
    security_issues: int
    documentation_ratio: float

class CodeQualityAnalyzer:
    """Comprehensive code quality analysis."""
    
    def __init__(self, source_dir: str = "src/"):
        self.source_dir = Path(source_dir)
        self.metrics_history: List[QualityMetrics] = []
    
    def analyze_file(self, file_path: Path) -> QualityMetrics:
        """Analyze individual Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return minimal metrics for unparseable files
            return QualityMetrics(
                timestamp=datetime.now().isoformat(),
                file_path=str(file_path),
                lines_of_code=len(content.splitlines()),
                cyclomatic_complexity=0,
                cognitive_complexity=0,
                maintainability_index=0.0,
                duplication_ratio=0.0,
                test_coverage=0.0,
                security_issues=0,
                documentation_ratio=0.0
            )
        
        # Calculate metrics
        lines_of_code = len([line for line in content.splitlines() if line.strip()])
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        cognitive_complexity = self._calculate_cognitive_complexity(tree)
        maintainability_index = self._calculate_maintainability_index(content, tree)
        documentation_ratio = self._calculate_documentation_ratio(tree)
        
        return QualityMetrics(
            timestamp=datetime.now().isoformat(),
            file_path=str(file_path),
            lines_of_code=lines_of_code,
            cyclomatic_complexity=cyclomatic_complexity,
            cognitive_complexity=cognitive_complexity,
            maintainability_index=maintainability_index,
            duplication_ratio=0.0,  # Calculated separately
            test_coverage=0.0,  # Retrieved from coverage reports
            security_issues=0,  # Retrieved from security scans
            documentation_ratio=documentation_ratio
        )
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity (simplified)."""
        complexity = 0
        nesting_level = 0
        
        class CognitiveComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                self.nesting_level = 0
            
            def visit_If(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_For(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_While(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
        
        visitor = CognitiveComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity
    
    def _calculate_maintainability_index(self, content: str, tree: ast.AST) -> float:
        """Calculate maintainability index (simplified)."""
        lines_of_code = len(content.splitlines())
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        
        # Simplified calculation
        if lines_of_code == 0:
            return 100.0
        
        # Halstead volume approximation
        halstead_volume = lines_of_code * 4.5  # Rough approximation
        
        # Maintainability index formula (simplified)
        mi = max(0, (171 - 5.2 * np.log(halstead_volume) - 
                    0.23 * cyclomatic_complexity - 
                    16.2 * np.log(lines_of_code)) * 100 / 171)
        
        return min(100.0, mi)
    
    def _calculate_documentation_ratio(self, tree: ast.AST) -> float:
        """Calculate documentation ratio."""
        total_functions = 0
        documented_functions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_functions += 1
                
                # Check if function/class has docstring
                if (ast.get_docstring(node) is not None):
                    documented_functions += 1
        
        if total_functions == 0:
            return 100.0
        
        return (documented_functions / total_functions) * 100.0
    
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze entire project."""
        python_files = list(self.source_dir.rglob("*.py"))
        file_metrics = []
        
        for file_path in python_files:
            if "test" in str(file_path) or "__pycache__" in str(file_path):
                continue
            
            metrics = self.analyze_file(file_path)
            file_metrics.append(metrics)
        
        # Calculate project-level aggregates
        total_loc = sum(m.lines_of_code for m in file_metrics)
        avg_complexity = sum(m.cyclomatic_complexity for m in file_metrics) / len(file_metrics) if file_metrics else 0
        avg_maintainability = sum(m.maintainability_index for m in file_metrics) / len(file_metrics) if file_metrics else 0
        avg_documentation = sum(m.documentation_ratio for m in file_metrics) / len(file_metrics) if file_metrics else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'project_metrics': {
                'total_files': len(file_metrics),
                'total_lines_of_code': total_loc,
                'average_cyclomatic_complexity': avg_complexity,
                'average_maintainability_index': avg_maintainability,
                'average_documentation_ratio': avg_documentation
            },
            'file_metrics': [asdict(m) for m in file_metrics],
            'quality_gates': self._evaluate_quality_gates(file_metrics)
        }
    
    def _evaluate_quality_gates(self, metrics: List[QualityMetrics]) -> Dict[str, Any]:
        """Evaluate quality gates."""
        violations = []
        
        for metric in metrics:
            if metric.cyclomatic_complexity > 15:
                violations.append({
                    'file': metric.file_path,
                    'violation': 'high_complexity',
                    'value': metric.cyclomatic_complexity,
                    'threshold': 15
                })
            
            if metric.maintainability_index < 60:
                violations.append({
                    'file': metric.file_path,
                    'violation': 'low_maintainability',
                    'value': metric.maintainability_index,
                    'threshold': 60
                })
            
            if metric.documentation_ratio < 70:
                violations.append({
                    'file': metric.file_path,
                    'violation': 'poor_documentation',
                    'value': metric.documentation_ratio,
                    'threshold': 70
                })
        
        return {
            'total_violations': len(violations),
            'violations': violations,
            'passed': len(violations) == 0
        }
    
    def generate_quality_report(self, output_file: str = "quality_report.json"):
        """Generate comprehensive quality report."""
        analysis_result = self.analyze_project()
        
        with open(output_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)
        
        return analysis_result

# Import numpy for calculations
try:
    import numpy as np
except ImportError:
    # Fallback for environments without numpy
    class MockNumpy:
        @staticmethod
        def log(x):
            import math
            return math.log(x)
    np = MockNumpy()
```

#### Technical Debt Dashboard

```python
# scripts/debt_dashboard.py
"""
Technical debt tracking dashboard generator.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

@dataclass
class DebtItem:
    """Technical debt item."""
    debt_id: str
    title: str
    description: str
    debt_type: str  # code, design, test, documentation, infrastructure
    severity: str   # low, medium, high, critical
    estimated_effort_hours: float
    created_date: datetime
    due_date: Optional[datetime]
    assigned_to: Optional[str]
    status: str  # open, in_progress, resolved, deferred
    file_path: Optional[str]
    tags: List[str]

class TechnicalDebtTracker:
    """Technical debt tracking and management system."""
    
    def __init__(self, db_path: str = "technical_debt.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize debt tracking database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debt_items (
                debt_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                debt_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                estimated_effort_hours REAL,
                created_date TEXT NOT NULL,
                due_date TEXT,
                assigned_to TEXT,
                status TEXT DEFAULT 'open',
                file_path TEXT,
                tags TEXT,
                resolved_date TEXT,
                actual_effort_hours REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debt_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_debt_items INTEGER,
                total_estimated_effort REAL,
                debt_by_type TEXT,
                debt_by_severity TEXT,
                resolution_rate REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_debt_item(self, debt_item: DebtItem) -> str:
        """Add technical debt item."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO debt_items 
            (debt_id, title, description, debt_type, severity, estimated_effort_hours,
             created_date, due_date, assigned_to, status, file_path, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            debt_item.debt_id,
            debt_item.title,
            debt_item.description,
            debt_item.debt_type,
            debt_item.severity,
            debt_item.estimated_effort_hours,
            debt_item.created_date.isoformat(),
            debt_item.due_date.isoformat() if debt_item.due_date else None,
            debt_item.assigned_to,
            debt_item.status,
            debt_item.file_path,
            json.dumps(debt_item.tags)
        ))
        conn.commit()
        conn.close()
        return debt_item.debt_id
    
    def update_debt_status(self, debt_id: str, status: str, 
                          actual_effort_hours: Optional[float] = None):
        """Update debt item status."""
        conn = sqlite3.connect(self.db_path)
        
        update_fields = ["status = ?"]
        params = [status, debt_id]
        
        if status == "resolved":
            update_fields.append("resolved_date = ?")
            params.insert(-1, datetime.now().isoformat())
        
        if actual_effort_hours is not None:
            update_fields.append("actual_effort_hours = ?")
            params.insert(-1, actual_effort_hours)
        
        query = f"UPDATE debt_items SET {', '.join(update_fields)} WHERE debt_id = ?"
        conn.execute(query, params)
        conn.commit()
        conn.close()
    
    def get_debt_summary(self) -> Dict[str, Any]:
        """Get technical debt summary."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total debt items by status
        cursor.execute("""
            SELECT status, COUNT(*), SUM(estimated_effort_hours)
            FROM debt_items 
            GROUP BY status
        """)
        status_summary = {row[0]: {'count': row[1], 'effort': row[2] or 0} 
                         for row in cursor.fetchall()}
        
        # Debt by type
        cursor.execute("""
            SELECT debt_type, COUNT(*), SUM(estimated_effort_hours)
            FROM debt_items 
            WHERE status != 'resolved'
            GROUP BY debt_type
        """)
        type_summary = {row[0]: {'count': row[1], 'effort': row[2] or 0} 
                       for row in cursor.fetchall()}
        
        # Debt by severity
        cursor.execute("""
            SELECT severity, COUNT(*), SUM(estimated_effort_hours)
            FROM debt_items 
            WHERE status != 'resolved'
            GROUP BY severity
        """)
        severity_summary = {row[0]: {'count': row[1], 'effort': row[2] or 0} 
                           for row in cursor.fetchall()}
        
        # Overdue items
        cursor.execute("""
            SELECT COUNT(*)
            FROM debt_items 
            WHERE status != 'resolved' 
            AND due_date IS NOT NULL 
            AND due_date < ?
        """, (datetime.now().isoformat(),))
        overdue_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'status_summary': status_summary,
            'type_summary': type_summary,
            'severity_summary': severity_summary,
            'overdue_count': overdue_count,
            'total_open_effort': sum(item['effort'] for item in status_summary.values() 
                                   if 'open' in status_summary or 'in_progress' in status_summary)
        }
    
    def generate_debt_trends(self, days: int = 90) -> Dict[str, Any]:
        """Generate debt trend analysis."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Generate daily snapshots
        daily_snapshots = []
        current_date = start_date
        
        while current_date <= end_date:
            snapshot = self._get_debt_snapshot(current_date)
            daily_snapshots.append({
                'date': current_date.isoformat(),
                'total_items': snapshot['total_items'],
                'total_effort': snapshot['total_effort'],
                'resolved_items': snapshot['resolved_items']
            })
            current_date += timedelta(days=1)
        
        return {
            'period_days': days,
            'daily_snapshots': daily_snapshots,
            'trends': self._calculate_trends(daily_snapshots)
        }
    
    def _get_debt_snapshot(self, date: datetime) -> Dict[str, Any]:
        """Get debt snapshot for specific date."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Items created by this date but not resolved
        cursor.execute("""
            SELECT COUNT(*), SUM(estimated_effort_hours)
            FROM debt_items 
            WHERE created_date <= ? 
            AND (resolved_date IS NULL OR resolved_date > ?)
        """, (date.isoformat(), date.isoformat()))
        
        result = cursor.fetchone()
        total_items = result[0] or 0
        total_effort = result[1] or 0
        
        # Items resolved by this date
        cursor.execute("""
            SELECT COUNT(*)
            FROM debt_items 
            WHERE resolved_date <= ?
        """, (date.isoformat(),))
        
        resolved_items = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_items': total_items,
            'total_effort': total_effort,
            'resolved_items': resolved_items
        }
    
    def _calculate_trends(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend metrics."""
        if len(snapshots) < 2:
            return {}
        
        # Calculate rates
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        
        items_change = last_snapshot['total_items'] - first_snapshot['total_items']
        effort_change = last_snapshot['total_effort'] - first_snapshot['total_effort']
        
        # Calculate resolution rate
        total_resolved = last_snapshot['resolved_items']
        total_created = max(s['total_items'] + s['resolved_items'] for s in snapshots)
        resolution_rate = (total_resolved / total_created * 100) if total_created > 0 else 0
        
        return {
            'items_change': items_change,
            'effort_change': effort_change,
            'resolution_rate': resolution_rate,
            'trend_direction': 'increasing' if items_change > 0 else 'decreasing' if items_change < 0 else 'stable'
        }
    
    def generate_dashboard_html(self, output_file: str = "debt_dashboard.html"):
        """Generate HTML dashboard."""
        summary = self.get_debt_summary()
        trends = self.generate_debt_trends()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Technical Debt Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric-card {{ 
                    border: 1px solid #ddd; 
                    border-radius: 8px; 
                    padding: 20px; 
                    margin: 10px; 
                    display: inline-block; 
                    min-width: 200px; 
                }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
                .metric-label {{ color: #666; }}
                .chart-container {{ width: 48%; display: inline-block; margin: 1%; }}
            </style>
        </head>
        <body>
            <h1>Technical Debt Dashboard</h1>
            <p>Generated: {summary['timestamp']}</p>
            
            <div class="metrics-row">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('status_summary', {}).get('open', {}).get('count', 0)}</div>
                    <div class="metric-label">Open Items</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_open_effort', 0):.1f}h</div>
                    <div class="metric-label">Estimated Effort</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">{summary.get('overdue_count', 0)}</div>
                    <div class="metric-label">Overdue Items</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="typeChart"></canvas>
            </div>
            
            <div class="chart-container">
                <canvas id="severityChart"></canvas>
            </div>
            
            <script>
                // Debt by type chart
                const typeCtx = document.getElementById('typeChart').getContext('2d');
                new Chart(typeCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: {list(summary.get('type_summary', {}).keys())},
                        datasets: [{{
                            data: {[item['count'] for item in summary.get('type_summary', {}).values()]},
                            backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            title: {{
                                display: true,
                                text: 'Debt by Type'
                            }}
                        }}
                    }}
                }});
                
                // Debt by severity chart
                const severityCtx = document.getElementById('severityChart').getContext('2d');
                new Chart(severityCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {list(summary.get('severity_summary', {}).keys())},
                        datasets: [{{
                            label: 'Count',
                            data: {[item['count'] for item in summary.get('severity_summary', {}).values()]},
                            backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            title: {{
                                display: true,
                                text: 'Debt by Severity'
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Debt dashboard generated: {output_file}")
        return output_file
```

## Automated Quality Gates

### Pre-commit Quality Checks

```bash
#!/bin/bash
# scripts/quality_gate.sh
# Automated quality gate script for pre-commit hooks

set -e

echo "🔍 Running quality gate checks..."

# Exit codes
QUALITY_GATE_PASSED=0
QUALITY_GATE_FAILED=1

# Configuration
MAX_COMPLEXITY=15
MIN_MAINTAINABILITY=60
MIN_COVERAGE=80
MAX_DEBT_ITEMS=10

# Run code quality analysis
echo "📊 Analyzing code quality..."
python scripts/code_quality_analyzer.py > quality_report.json

# Extract metrics
TOTAL_VIOLATIONS=$(jq '.quality_gates.total_violations' quality_report.json)
AVG_COMPLEXITY=$(jq '.project_metrics.average_cyclomatic_complexity' quality_report.json)
AVG_MAINTAINABILITY=$(jq '.project_metrics.average_maintainability_index' quality_report.json)

# Check complexity threshold
if (( $(echo "$AVG_COMPLEXITY > $MAX_COMPLEXITY" | bc -l) )); then
    echo "❌ Average complexity too high: $AVG_COMPLEXITY (max: $MAX_COMPLEXITY)"
    exit $QUALITY_GATE_FAILED
fi

# Check maintainability threshold
if (( $(echo "$AVG_MAINTAINABILITY < $MIN_MAINTAINABILITY" | bc -l) )); then
    echo "❌ Maintainability too low: $AVG_MAINTAINABILITY (min: $MIN_MAINTAINABILITY)"
    exit $QUALITY_GATE_FAILED
fi

# Check for quality violations
if [ "$TOTAL_VIOLATIONS" -gt 0 ]; then
    echo "❌ Quality violations found: $TOTAL_VIOLATIONS"
    jq '.quality_gates.violations[] | "\(.file): \(.violation) (\(.value))"' quality_report.json
    exit $QUALITY_GATE_FAILED
fi

# Check test coverage
if command -v coverage &> /dev/null; then
    COVERAGE=$(coverage report --format=total 2>/dev/null || echo "0")
    if [ "$COVERAGE" -lt "$MIN_COVERAGE" ]; then
        echo "❌ Test coverage too low: $COVERAGE% (min: $MIN_COVERAGE%)"
        exit $QUALITY_GATE_FAILED
    fi
    echo "✅ Test coverage: $COVERAGE%"
fi

# Check technical debt
if [ -f "technical_debt.db" ]; then
    OPEN_DEBT_ITEMS=$(python -c "
import sqlite3
conn = sqlite3.connect('technical_debt.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM debt_items WHERE status != \"resolved\"')
print(cursor.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")

    if [ "$OPEN_DEBT_ITEMS" -gt "$MAX_DEBT_ITEMS" ]; then
        echo "⚠️  High technical debt: $OPEN_DEBT_ITEMS open items (max: $MAX_DEBT_ITEMS)"
        # Don't fail for debt, just warn
    fi
fi

echo "✅ All quality gates passed!"
echo "📈 Metrics: Complexity=$AVG_COMPLEXITY, Maintainability=$AVG_MAINTAINABILITY"
exit $QUALITY_GATE_PASSED
```

### CI/CD Quality Pipeline

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality-analysis:
    name: Code Quality Analysis
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for quality trends
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install matplotlib pandas jq bc
      
      - name: Run quality analysis
        run: |
          python scripts/code_quality_analyzer.py
          python scripts/debt_dashboard.py --update-metrics
      
      - name: Check quality gates
        run: |
          chmod +x scripts/quality_gate.sh
          ./scripts/quality_gate.sh
      
      - name: Generate quality report
        if: always()
        run: |
          python scripts/debt_dashboard.py --generate-report
      
      - name: Upload quality artifacts
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: quality-reports
          path: |
            quality_report.json
            debt_dashboard.html
            *.png
      
      - name: Comment PR with quality summary
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const qualityReport = JSON.parse(fs.readFileSync('quality_report.json', 'utf8'));
            
            const comment = `## 📊 Code Quality Report
            
            **Project Metrics:**
            - Average Complexity: ${qualityReport.project_metrics.average_cyclomatic_complexity.toFixed(2)}
            - Maintainability Index: ${qualityReport.project_metrics.average_maintainability_index.toFixed(2)}
            - Documentation Ratio: ${qualityReport.project_metrics.average_documentation_ratio.toFixed(2)}%
            
            **Quality Gates:** ${qualityReport.quality_gates.passed ? '✅ PASSED' : '❌ FAILED'}
            
            ${qualityReport.quality_gates.total_violations > 0 ? 
              `**Violations:** ${qualityReport.quality_gates.total_violations}` : 
              '**No violations found**'}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });

  debt-tracking:
    name: Technical Debt Tracking
    runs-on: ubuntu-latest
    needs: quality-analysis
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Update debt tracking
        run: |
          python scripts/auto_debt_detection.py
          python scripts/debt_dashboard.py --update-trends
      
      - name: Check debt thresholds
        run: |
          CRITICAL_DEBT=$(python -c "
          import json
          with open('debt_summary.json') as f:
              data = json.load(f)
          print(data.get('severity_summary', {}).get('critical', {}).get('count', 0))
          ")
          
          if [ "$CRITICAL_DEBT" -gt 0 ]; then
            echo "🚨 Critical technical debt items found: $CRITICAL_DEBT"
            echo "Please address critical debt items before merging."
            exit 1
          fi
```

## Quality Improvement Strategies

### Debt Remediation Prioritization

```python
# scripts/debt_prioritization.py
"""
Technical debt prioritization algorithm.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np

@dataclass
class DebtPriority:
    """Debt item with calculated priority score."""
    debt_item: DebtItem
    priority_score: float
    business_impact: float
    technical_impact: float
    remediation_effort: float

class DebtPrioritizer:
    """Algorithm for prioritizing technical debt remediation."""
    
    def __init__(self):
        # Weights for different factors (sum to 1.0)
        self.weights = {
            'severity': 0.3,
            'business_impact': 0.25,
            'technical_impact': 0.25,
            'effort_ratio': 0.2
        }
    
    def calculate_priority(self, debt_items: List[DebtItem]) -> List[DebtPriority]:
        """Calculate priority scores for debt items."""
        priorities = []
        
        for item in debt_items:
            # Severity score (0-1)
            severity_scores = {'low': 0.25, 'medium': 0.5, 'high': 0.75, 'critical': 1.0}
            severity_score = severity_scores.get(item.severity, 0.5)
            
            # Business impact score (0-1)
            business_impact = self._calculate_business_impact(item)
            
            # Technical impact score (0-1)
            technical_impact = self._calculate_technical_impact(item)
            
            # Effort ratio (inverse - lower effort = higher score)
            max_effort = max(i.estimated_effort_hours or 1 for i in debt_items)
            effort_ratio = 1.0 - ((item.estimated_effort_hours or 1) / max_effort)
            
            # Calculate weighted priority score
            priority_score = (
                self.weights['severity'] * severity_score +
                self.weights['business_impact'] * business_impact +
                self.weights['technical_impact'] * technical_impact +
                self.weights['effort_ratio'] * effort_ratio
            )
            
            priorities.append(DebtPriority(
                debt_item=item,
                priority_score=priority_score,
                business_impact=business_impact,
                technical_impact=technical_impact,
                remediation_effort=item.estimated_effort_hours or 0
            ))
        
        # Sort by priority score (highest first)
        return sorted(priorities, key=lambda x: x.priority_score, reverse=True)
    
    def _calculate_business_impact(self, item: DebtItem) -> float:
        """Calculate business impact score."""
        impact_factors = {
            'affects_security': 0.9,
            'affects_performance': 0.8,
            'affects_user_experience': 0.7,
            'affects_compliance': 0.8,
            'blocks_development': 0.6,
            'increases_support_burden': 0.5
        }
        
        # Check tags for impact indicators
        impact_score = 0.3  # Base score
        for tag in item.tags:
            for factor, score in impact_factors.items():
                if factor in tag.lower():
                    impact_score = max(impact_score, score)
        
        return min(1.0, impact_score)
    
    def _calculate_technical_impact(self, item: DebtItem) -> float:
        """Calculate technical impact score."""
        type_impacts = {
            'code': 0.6,
            'design': 0.8,
            'test': 0.5,
            'documentation': 0.3,
            'infrastructure': 0.7
        }
        
        base_impact = type_impacts.get(item.debt_type, 0.5)
        
        # Adjust based on file location (core files have higher impact)
        if item.file_path:
            if 'core' in item.file_path or 'scanner' in item.file_path:
                base_impact *= 1.2
            elif 'test' in item.file_path:
                base_impact *= 0.8
        
        return min(1.0, base_impact)
    
    def generate_remediation_plan(self, debt_items: List[DebtItem], 
                                 sprint_capacity_hours: float = 40) -> Dict[str, Any]:
        """Generate remediation plan based on capacity."""
        priorities = self.calculate_priority(debt_items)
        
        # Group into sprints based on capacity
        sprints = []
        current_sprint = []
        current_capacity = 0
        
        for priority in priorities:
            if priority.debt_item.status != 'open':
                continue
            
            effort = priority.remediation_effort
            if current_capacity + effort <= sprint_capacity_hours:
                current_sprint.append(priority)
                current_capacity += effort
            else:
                if current_sprint:
                    sprints.append({
                        'items': current_sprint,
                        'total_effort': current_capacity,
                        'estimated_impact': sum(p.priority_score for p in current_sprint)
                    })
                current_sprint = [priority]
                current_capacity = effort
        
        # Add remaining items
        if current_sprint:
            sprints.append({
                'items': current_sprint,
                'total_effort': current_capacity,
                'estimated_impact': sum(p.priority_score for p in current_sprint)
            })
        
        return {
            'total_debt_items': len([p for p in priorities if p.debt_item.status == 'open']),
            'total_estimated_effort': sum(p.remediation_effort for p in priorities if p.debt_item.status == 'open'),
            'sprints': sprints,
            'recommendations': self._generate_recommendations(priorities)
        }
    
    def _generate_recommendations(self, priorities: List[DebtPriority]) -> List[str]:
        """Generate remediation recommendations."""
        recommendations = []
        
        critical_items = [p for p in priorities if p.debt_item.severity == 'critical' and p.debt_item.status == 'open']
        if critical_items:
            recommendations.append(f"🚨 Address {len(critical_items)} critical debt items immediately")
        
        high_impact_items = [p for p in priorities if p.business_impact > 0.8 and p.debt_item.status == 'open']
        if high_impact_items:
            recommendations.append(f"📈 Prioritize {len(high_impact_items)} high business impact items")
        
        quick_wins = [p for p in priorities if p.remediation_effort < 4 and p.priority_score > 0.6 and p.debt_item.status == 'open']
        if quick_wins:
            recommendations.append(f"⚡ Consider {len(quick_wins)} quick win items for immediate improvement")
        
        return recommendations
```

## Integration with Development Workflow

### Quality-Aware Development Process

1. **Pre-Development**
   - Review technical debt backlog
   - Allocate 20% of sprint capacity to debt remediation
   - Select debt items related to planned features

2. **During Development**
   - Run quality checks on every commit
   - Monitor quality metrics in real-time
   - Address new debt items immediately

3. **Code Review Process**
   - Include quality metrics in PR reviews
   - Require approval for quality gate violations
   - Document new technical debt items

4. **Sprint Planning**
   - Include debt remediation in sprint goals
   - Balance new features with quality improvements
   - Track debt trends and set improvement targets

This comprehensive technical debt tracking and code quality metrics framework ensures continuous improvement and maintainability of the Agentic RedTeam Radar codebase.