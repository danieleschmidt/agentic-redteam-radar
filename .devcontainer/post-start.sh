#!/bin/bash
# Post-start script - runs every time the container starts

set -e

echo "🔄 Container starting up..."

# Ensure virtual environment is activated
source /opt/venv/bin/activate

# Wait for dependent services to be ready
echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL
echo "  🐘 Waiting for PostgreSQL..."
timeout=30
count=0
while ! nc -z postgres 5432 && [ $count -lt $timeout ]; do
    sleep 1
    ((count++))
done

if [ $count -eq $timeout ]; then
    echo "  ⚠️  PostgreSQL not ready after ${timeout}s, continuing anyway..."
else
    echo "  ✅ PostgreSQL is ready"
fi

# Wait for Redis
echo "  🟥 Waiting for Redis..."
count=0
while ! nc -z redis 6379 && [ $count -lt $timeout ]; do
    sleep 1
    ((count++))
done

if [ $count -eq $timeout ]; then
    echo "  ⚠️  Redis not ready after ${timeout}s, continuing anyway..."
else
    echo "  ✅ Redis is ready"
fi

# Update PATH in current session
export PATH="/opt/venv/bin:$HOME/.local/bin:$PATH"

# Show container status
echo "🏃 Container is ready!"
echo ""
echo "📊 Service status:"
nc -z postgres 5432 && echo "  ✅ PostgreSQL (postgres:5432)" || echo "  ❌ PostgreSQL (postgres:5432)"
nc -z redis 6379 && echo "  ✅ Redis (redis:6379)" || echo "  ❌ Redis (redis:6379)"
nc -z minio 9000 && echo "  ✅ MinIO (minio:9000)" || echo "  ❌ MinIO (minio:9000)"
nc -z prometheus 9090 && echo "  ✅ Prometheus (prometheus:9090)" || echo "  ❌ Prometheus (prometheus:9090)"
nc -z grafana 3000 && echo "  ✅ Grafana (grafana:3000)" || echo "  ❌ Grafana (grafana:3000)"
echo ""

# Show useful information
echo "💡 Development tips:"
echo "  - Run 'test' to execute tests"
echo "  - Run 'lint' to check code quality"
echo "  - Run 'radar --help' to see CLI options"
echo "  - Open http://localhost:3000 for Grafana (admin/admin)"
echo "  - Open http://localhost:9090 for Prometheus"
echo ""