#!/bin/bash
# Post-attach script - runs when attaching to an existing container

set -e

echo "🔗 Attaching to development container..."

# Ensure we're in the workspace
cd /workspace

# Activate virtual environment
source /opt/venv/bin/activate

# Update PATH
export PATH="/opt/venv/bin:$HOME/.local/bin:$PATH"

# Show quick status
echo "📍 Current location: $(pwd)"
echo "🐍 Python version: $(python --version)"
echo "📦 Virtual environment: $(which python)"

# Check if the package is installed
if python -c "import agentic_redteam" 2>/dev/null; then
    echo "✅ Package is installed and ready"
else
    echo "⚠️  Package not found - run 'pip install -e .' to install"
fi

# Show recent changes if git is available
if [ -d ".git" ]; then
    echo ""
    echo "📝 Recent commits:"
    git log --oneline -5 2>/dev/null || echo "  No git history available"
fi

echo ""
echo "🚀 Ready for development!"
echo ""