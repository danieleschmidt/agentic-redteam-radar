#!/bin/bash
set -e

echo "🚀 Setting up Agentic RedTeam Radar development environment..."

# Update system packages
apt-get update && apt-get install -y \
    curl \
    git \
    make \
    build-essential \
    sqlite3 \
    redis-server \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
mkdir -p /tmp/radar-cache
mkdir -p /tmp/radar-logs
mkdir -p reports

# Set permissions
chmod 755 /tmp/radar-cache
chmod 755 /tmp/radar-logs
chmod 755 reports

# Install additional security tools
echo "🔒 Installing security tools..."
pip install safety bandit semgrep

# Setup git config if not already configured
if [ -z "$(git config --global user.email)" ]; then
    echo "⚙️  Setting up git configuration..."
    git config --global user.email "developer@terragonlabs.com"
    git config --global user.name "Terragon Developer"
    git config --global init.defaultBranch main
fi

# Create environment template
cat > .env.template << 'EOF'
# API Keys (required for testing)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Radar Configuration
RADAR_LOG_LEVEL=INFO
RADAR_MAX_CONCURRENCY=5
RADAR_TIMEOUT=30
RADAR_OUTPUT_DIR=./reports
RADAR_CACHE_ENABLED=true

# Development Settings
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1

# Database (for future use)
DATABASE_URL=sqlite:///./radar.db
REDIS_URL=redis://localhost:6379/0
EOF

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Copy .env.template to .env and add your API keys"
echo "2. Run 'make test' to verify installation"
echo "3. Run 'radar --help' to see CLI options"
echo "4. Start developing with 'make dev'"