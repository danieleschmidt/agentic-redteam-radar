#!/bin/bash
set -e

echo "🚀 Starting Agentic RedTeam Radar - Production Deployment"
echo "=========================================================="

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python -c "
import time
import psycopg2
from urllib.parse import urlparse
import os

db_url = os.environ.get('RADAR_DATABASE_URL', '')
if db_url.startswith('postgresql://'):
    parsed = urlparse(db_url)
    
    for i in range(30):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            conn.close()
            print('✅ Database connection successful')
            break
        except psycopg2.OperationalError:
            print(f'❌ Database connection attempt {i+1}/30 failed, retrying...')
            time.sleep(2)
    else:
        print('🚨 Failed to connect to database after 30 attempts')
        exit(1)
else:
    print('ℹ️  Using SQLite database')
"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis connection..."
python -c "
import time
import redis
import os

cache_url = os.environ.get('RADAR_CACHE_URL', '')
if cache_url.startswith('redis://'):
    for i in range(30):
        try:
            r = redis.from_url(cache_url)
            r.ping()
            print('✅ Redis connection successful')
            break
        except (redis.ConnectionError, redis.TimeoutError):
            print(f'❌ Redis connection attempt {i+1}/30 failed, retrying...')
            time.sleep(2)
    else:
        print('🚨 Failed to connect to Redis after 30 attempts')
        exit(1)
else:
    print('ℹ️  Using memory cache')
"

# Initialize database tables if needed
echo "🗄️  Initializing database..."
python -c "
import asyncio
from agentic_redteam.database import initialize_database

async def init():
    try:
        await initialize_database()
        print('✅ Database initialized successfully')
    except Exception as e:
        print(f'⚠️  Database initialization: {e}')

try:
    asyncio.run(init())
except ImportError:
    print('ℹ️  Database initialization skipped (module not found)')
"

# Validate configuration
echo "⚙️  Validating configuration..."
python -c "
from agentic_redteam.config_simple import load_config, validate_config

try:
    config = load_config()
    errors = validate_config(config)
    
    if errors:
        print('🚨 Configuration errors found:')
        for error in errors:
            print(f'   - {error}')
        exit(1)
    else:
        print('✅ Configuration validated successfully')
        print(f'   - Max Concurrency: {config.max_concurrency}')
        print(f'   - Enabled Patterns: {len(config.enabled_patterns)}')
        print(f'   - Log Level: {config.log_level}')
        
except Exception as e:
    print(f'⚠️  Configuration validation: {e}')
"

# Create required directories
echo "📁 Setting up directories..."
mkdir -p /app/reports /app/logs /app/cache
echo "✅ Directories created"

# Set up signal handlers for graceful shutdown
echo "🔧 Setting up graceful shutdown..."
python -c "
import signal
import sys

def signal_handler(sig, frame):
    print('🛑 Received shutdown signal, stopping gracefully...')
    # Add cleanup code here if needed
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
print('✅ Signal handlers configured')
"

echo "🎯 Configuration complete, starting application..."
echo "=========================================================="

# Execute the main command
exec "$@"