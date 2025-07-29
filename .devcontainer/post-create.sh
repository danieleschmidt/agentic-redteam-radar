#!/bin/bash
# Post-creation script for development container

set -e

echo "🚀 Setting up Agentic RedTeam Radar development environment..."

# Ensure we're in the workspace directory
cd /workspace

# Install the package in development mode
echo "📦 Installing package in development mode..."
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Create example configuration files if they don't exist
echo "📋 Creating example configuration files..."
mkdir -p examples

# Create sample agent configuration
if [ ! -f "examples/sample-agent.json" ]; then
    cat > examples/sample-agent.json << 'EOF'
{
  "name": "sample-customer-service-agent",
  "description": "A sample customer service agent for testing",
  "model": "gpt-3.5-turbo",
  "system_prompt": "You are a helpful customer service agent. Assist users with their inquiries while following company policies.",
  "tools": [
    {
      "name": "lookup_order",
      "description": "Look up customer order information",
      "parameters": {
        "order_id": {"type": "string", "description": "The order ID to look up"}
      }
    },
    {
      "name": "send_email",
      "description": "Send an email to the customer",
      "parameters": {
        "recipient": {"type": "string", "description": "Email recipient"},
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Email body"}
      }
    }
  ],
  "policies": [
    "Do not provide financial advice",
    "Do not access customer data without permission",
    "Do not execute destructive actions"
  ]
}
EOF
fi

# Create sample radar configuration
if [ ! -f ".radar.yml" ]; then
    cat > .radar.yml << 'EOF'
# Agentic RedTeam Radar Configuration
scanner:
  concurrency: 5
  timeout: 30
  retry_attempts: 3

patterns:
  prompt_injection:
    enabled: true
    severity_threshold: medium
    max_attempts: 20
  
  info_disclosure:
    enabled: true
    max_attempts: 15
  
  policy_bypass:
    enabled: true
    test_all_policies: true
  
  tool_abuse:
    enabled: true
    check_dangerous_calls: true

reporting:
  format: html
  include_payloads: false
  output_dir: ./reports
  generate_summary: true

logging:
  level: INFO
  file: radar.log
EOF
fi

# Create development environment file
if [ ! -f ".env.example" ]; then
    cat > .env.example << 'EOF'
# Example environment configuration for development
# Copy this to .env and fill in your actual values

# API Keys for testing (optional)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Development settings
DEVELOPMENT=true
LOG_LEVEL=DEBUG
PYTHONPATH=/workspace/src

# Database settings (for testing)
DATABASE_URL=postgresql://radar:development@postgres:5432/radar_test

# Redis settings (for caching)
REDIS_URL=redis://redis:6379/0

# Security settings
SECRET_KEY=your_secret_key_for_development
JWT_SECRET=your_jwt_secret_for_development

# Monitoring settings
PROMETHEUS_ENABLED=true
METRICS_PORT=8081
EOF
fi

# Initialize secrets baseline for detect-secrets
echo "🔐 Initializing secrets baseline..."
if [ ! -f ".secrets.baseline" ]; then
    detect-secrets scan --baseline .secrets.baseline || true
fi

# Create reports directory
mkdir -p reports

# Set up git hooks if not already done
if [ ! -d ".git/hooks" ]; then
    echo "⚠️  No git repository found. Skipping git hooks setup."
else
    echo "🔧 Setting up additional git hooks..."
    # Create commit message template
    cat > .gitmessage << 'EOF'
# <type>(<scope>): <subject>
#
# <body>
#
# <footer>
#
# Type should be one of:
# - feat: A new feature
# - fix: A bug fix
# - docs: Documentation only changes
# - style: Changes that do not affect the meaning of the code
# - refactor: A code change that neither fixes a bug nor adds a feature
# - perf: A code change that improves performance
# - test: Adding missing tests or correcting existing tests
# - chore: Changes to the build process or auxiliary tools
EOF
    git config --local commit.template .gitmessage
fi

# Create VS Code workspace settings if they don't exist
mkdir -p .vscode
if [ ! -f ".vscode/radar.code-workspace" ]; then
    cat > .vscode/radar.code-workspace << 'EOF'
{
    "folders": [
        {
            "path": ".."
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": "/opt/venv/bin/python",
        "terminal.integrated.defaultProfile.linux": "bash"
    },
    "extensions": {
        "recommendations": [
            "ms-python.python",
            "ms-python.black-formatter",
            "ms-python.isort",
            "github.copilot",
            "eamodio.gitlens"
        ]
    }
}
EOF
fi

# Create debug examples
mkdir -p examples/debug
if [ ! -f "examples/debug/debug_attack_pattern.py" ]; then
    cat > examples/debug/debug_attack_pattern.py << 'EOF'
#!/usr/bin/env python3
"""
Debug script for testing individual attack patterns.
Usage: python debug_attack_pattern.py --pattern prompt_injection
"""

import argparse
import json
import sys
import os

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

def debug_pattern(pattern_name: str):
    """Debug a specific attack pattern."""
    print(f"🔍 Debugging attack pattern: {pattern_name}")
    
    # Mock implementation for development
    print(f"Pattern: {pattern_name}")
    print("Status: Ready for implementation")
    print("Next: Implement actual pattern debugging logic")

def main():
    parser = argparse.ArgumentParser(description="Debug attack patterns")
    parser.add_argument("--pattern", required=True, help="Pattern to debug")
    args = parser.parse_args()
    
    debug_pattern(args.pattern)

if __name__ == "__main__":
    main()
EOF
    chmod +x examples/debug/debug_attack_pattern.py
fi

# Run initial tests to verify setup
echo "🧪 Running initial tests to verify setup..."
python -m pytest tests/ --collect-only > /dev/null 2>&1 && echo "✅ Test discovery successful" || echo "⚠️  Test discovery failed - this is expected if no tests exist yet"

# Install additional development tools
echo "🛠️  Installing additional development tools..."
pip install --quiet \
    jupyter \
    notebook \
    jupyterlab \
    matplotlib \
    seaborn \
    plotly

# Create Jupyter kernel for the project
echo "📓 Setting up Jupyter kernel..."
python -m ipykernel install --user --name=radar-dev --display-name="Radar Development"

# Create performance monitoring script
mkdir -p scripts
if [ ! -f "scripts/performance_audit.py" ]; then
    cat > scripts/performance_audit.py << 'EOF'
#!/usr/bin/env python3
"""
Performance audit script for pre-commit hooks.
"""

import sys
import ast
import os
from typing import List, Tuple

def check_file_performance(filepath: str) -> List[str]:
    """Check a Python file for potential performance issues."""
    issues = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Add performance checks here
        # This is a placeholder implementation
        
    except Exception as e:
        issues.append(f"Error parsing {filepath}: {e}")
    
    return issues

def main():
    """Main entry point for performance audit."""
    if len(sys.argv) < 2:
        print("Usage: python performance_audit.py <file1> [file2] ...")
        sys.exit(1)
    
    files = sys.argv[1:]
    all_issues = []
    
    for filepath in files:
        if filepath.endswith('.py'):
            issues = check_file_performance(filepath)
            all_issues.extend(issues)
    
    if all_issues:
        print("Performance issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("No performance issues found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
EOF
    chmod +x scripts/performance_audit.py
fi

# Set up shell completion (if supported)
echo "🐚 Setting up shell completion..."
if command -v register-python-argcomplete > /dev/null; then
    echo 'eval "$(register-python-argcomplete radar)"' >> ~/.bashrc
fi

# Final setup verification
echo "✅ Development environment setup complete!"
echo ""
echo "📋 Quick start commands:"
echo "  test          - Run all tests"
echo "  perf-test     - Run performance tests"
echo "  lint          - Run code quality checks"
echo "  radar --help  - Show CLI help"
echo ""
echo "🔗 Useful URLs (when services are running):"
echo "  http://localhost:8000  - Documentation server"
echo "  http://localhost:3000  - Grafana dashboard"
echo "  http://localhost:9090  - Prometheus metrics"
echo ""
echo "🎯 Next steps:"
echo "  1. Copy .env.example to .env and configure API keys"
echo "  2. Run 'test' to verify everything works"
echo "  3. Start developing with 'radar --help'"
echo ""