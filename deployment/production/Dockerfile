# Multi-stage Dockerfile for production deployment
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r radar && useradd -r -g radar radar

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install -e .

# Development stage
FROM base as development

# Install development dependencies
RUN pip install pytest pytest-asyncio pytest-cov memory-profiler black isort flake8

# Copy source code
COPY . .

# Change ownership
RUN chown -R radar:radar /app
USER radar

EXPOSE 8080
CMD ["python", "-m", "agentic_redteam.server", "--host", "0.0.0.0", "--port", "8080"]

# Production stage
FROM base as production

# Copy only necessary files
COPY src/ ./src/
COPY deployment/production/entrypoint.sh ./entrypoint.sh
COPY deployment/production/healthcheck.py ./healthcheck.py

# Install production dependencies only
RUN pip install gunicorn uvicorn fastapi

# Create necessary directories
RUN mkdir -p /app/reports /app/logs /app/cache

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Change ownership
RUN chown -R radar:radar /app
USER radar

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python healthcheck.py

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-", "agentic_redteam.server:app"]