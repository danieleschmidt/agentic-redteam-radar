# Multi-stage Dockerfile for Agentic RedTeam Radar
# Optimized for security, performance, and minimal attack surface

# Build stage
FROM python:3.13-slim as builder

# Security: Create non-root user
RUN groupadd -r radar && useradd -r -g radar radar

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package
RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.13-slim as production

# Security: Install security updates
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Create non-root user
RUN groupadd -r radar && useradd -r -g radar radar

# Set work directory
WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY --from=builder /app/src ./src
COPY --from=builder /app/README.md /app/LICENSE ./

# Create directories for reports and logs
RUN mkdir -p /app/reports /app/logs \
    && chown -R radar:radar /app

# Security: Switch to non-root user
USER radar

# Set environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RADAR_OUTPUT_DIR=/app/reports \
    RADAR_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import agentic_redteam; print('OK')" || exit 1

# Expose port (if web interface is added)
EXPOSE 8000

# Default command
CMD ["radar", "--help"]

# Development stage (for development use)
FROM production as development

# Switch back to root to install dev dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        vim \
        less \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
        pytest \
        pytest-cov \
        black \
        isort \
        flake8 \
        mypy \
        pre-commit

# Switch back to radar user
USER radar

# Development command
CMD ["bash"]