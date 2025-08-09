#!/bin/bash
set -e

echo "🚀 Starting Agentic RedTeam Radar Production Deployment"
echo "============================================================="

# Wait for dependencies
echo "⏳ Waiting for database connection..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✅ Database connection established"

echo "⏳ Waiting for Redis connection..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "✅ Redis connection established"

# Initialize database if needed
if [ "$1" = "init-db" ]; then
    echo "🗄️  Initializing database schema..."
    python -c "
from agentic_redteam.database import init_database
init_database()
print('✅ Database initialized successfully')
"
    exit 0
fi

# Run database migrations if needed
echo "🔄 Running database migrations..."
python -c "
try:
    from agentic_redteam.database import run_migrations
    run_migrations()
    print('✅ Database migrations completed')
except Exception as e:
    print(f'⚠️  Migration warning: {e}')
"

# Validate configuration
echo "🔍 Validating configuration..."
python -c "
from agentic_redteam import RadarConfig
try:
    config = RadarConfig()
    print(f'✅ Configuration valid - Environment: {config.environment}')
    print(f'   - Database: {config.database.url[:20]}...')
    print(f'   - Cache: {config.cache.backend}')
    print(f'   - Max Concurrency: {config.scanner.max_concurrency}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    exit(1)
"

# Set resource limits if not in container
if [ ! -f /.dockerenv ]; then
    echo "📊 Setting resource limits..."
    ulimit -n 65536  # Open files
    ulimit -u 32768  # Max processes
fi

# Start health monitoring in background
echo "🏥 Starting health monitoring..."
python -c "
import asyncio
import signal
import sys
from agentic_redteam.monitoring.health_monitor import start_health_monitor

def signal_handler(signum, frame):
    print('🛑 Health monitor shutting down...')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

try:
    asyncio.run(start_health_monitor())
except KeyboardInterrupt:
    print('🛑 Health monitor stopped')
" &

# Start the main application
echo "🎯 Starting Agentic RedTeam Radar API Server..."
echo "   - Workers: 4"
echo "   - Bind: 0.0.0.0:8000"
echo "   - Worker Class: uvicorn.workers.UvicornWorker"
echo "============================================================="

exec "$@"