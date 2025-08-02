#\!/bin/bash

echo "🚀 Setting up Agentic RedTeam Radar development environment..."

# Update package lists
sudo apt-get update

# Install development dependencies
sudo apt-get install -y \
    build-essential \
    curl \
    git \
    jq \
    vim \
    htop \
    tree \
    unzip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install project dependencies in development mode
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Setup git configuration for better development experience
git config --global core.autocrlf false
git config --global core.filemode false
git config --global push.default simple

# Create necessary directories
mkdir -p ~/.local/bin
mkdir -p ~/workspace/logs
mkdir -p ~/workspace/reports
mkdir -p ~/workspace/temp

# Set up shell aliases for common tasks
cat >> ~/.bashrc << 'INNER_EOF'

# Agentic RedTeam Radar Development Aliases
alias radar='python -m agentic_redteam.cli'
alias pytest-cov='pytest --cov=agentic_redteam --cov-report=html --cov-report=term'
alias lint-all='flake8 src tests && mypy src && black --check src tests && isort --check-only src tests'
alias format-all='black src tests && isort src tests'
alias test-all='pytest tests/ -v'
alias build-docs='mkdocs build'
alias serve-docs='mkdocs serve --dev-addr=0.0.0.0:8000'

# Docker aliases
alias dc='docker-compose'
alias dcu='docker-compose up'
alias dcd='docker-compose down'
alias dcr='docker-compose run --rm'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

INNER_EOF

# Install additional development tools
echo "🛠️ Installing additional development tools..."

# Install ruff for fast linting
pip install ruff

# Install security tools
pip install bandit safety pip-audit

# Install performance tools
pip install line_profiler memory_profiler

echo "✅ Development environment setup complete\!"
echo ""
echo "Available commands:"
echo "  radar --help           - Main CLI interface"
echo "  pytest-cov           - Run tests with coverage"
echo "  lint-all             - Run all linting tools"
echo "  format-all           - Format code with black and isort"
echo "  test-all             - Run all tests"
echo "  build-docs           - Build documentation"
echo "  serve-docs           - Serve docs locally"
echo ""
echo "Happy coding\! 🎉"
EOF < /dev/null
