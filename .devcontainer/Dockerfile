# Development container for Agentic RedTeam Radar
ARG VARIANT="3.10"
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        build-essential \
        curl \
        git \
        gnupg \
        lsb-release \
        software-properties-common \
        wget \
        vim \
        nano \
        htop \
        tree \
        jq \
        unzip \
        zip \
        ca-certificates \
        # Database clients
        postgresql-client \
        redis-tools \
        # Security tools
        nmap \
        netcat \
        tcpdump \
        # Development tools
        shellcheck \
        yamllint \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for Docker-outside-of-Docker)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Install Helm
RUN curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | tee /usr/share/keyrings/helm.gpg > /dev/null \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list \
    && apt-get update \
    && apt-get install -y helm \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform (for infrastructure as code)
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y terraform \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel setuptools

# Install Python development tools
RUN pip install \
    # Code formatting and linting
    black \
    isort \
    flake8 \
    pylint \
    mypy \
    bandit \
    # Testing
    pytest \
    pytest-cov \
    pytest-xdist \
    pytest-benchmark \
    pytest-asyncio \
    hypothesis \
    faker \
    # Security tools
    pip-audit \
    safety \
    cyclonedx-bom \
    # Performance tools
    memory-profiler \
    py-spy \
    # Documentation
    mkdocs \
    mkdocs-material \
    mkdocstrings[python] \
    # Development utilities
    ipython \
    ipdb \
    rich \
    typer \
    # Pre-commit
    pre-commit \
    # Build tools
    build \
    twine

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Set up user permissions
RUN usermod -aG docker vscode

# Create workspace directory
RUN mkdir -p /workspace && chown vscode:vscode /workspace

# Switch to vscode user
USER vscode

# Set working directory
WORKDIR /workspace

# Create useful aliases and environment setup
RUN echo 'alias ll="ls -la"' >> ~/.bashrc \
    && echo 'alias la="ls -la"' >> ~/.bashrc \
    && echo 'alias l="ls -CF"' >> ~/.bashrc \
    && echo 'alias ..="cd .."' >> ~/.bashrc \
    && echo 'alias ...="cd ../.."' >> ~/.bashrc \
    && echo 'alias grep="grep --color=auto"' >> ~/.bashrc \
    && echo 'alias fgrep="fgrep --color=auto"' >> ~/.bashrc \
    && echo 'alias egrep="egrep --color=auto"' >> ~/.bashrc \
    && echo 'export PATH="/opt/venv/bin:$PATH"' >> ~/.bashrc \
    && echo 'export PYTHONPATH="/workspace/src:$PYTHONPATH"' >> ~/.bashrc

# Create development shortcuts
RUN mkdir -p ~/.local/bin \
    && echo '#!/bin/bash\ncd /workspace && python -m pytest tests/ "$@"' > ~/.local/bin/test \
    && echo '#!/bin/bash\ncd /workspace && python -m pytest tests/performance/ -m performance "$@"' > ~/.local/bin/perf-test \
    && echo '#!/bin/bash\ncd /workspace && pre-commit run --all-files "$@"' > ~/.local/bin/lint \
    && echo '#!/bin/bash\ncd /workspace && python -m agentic_redteam.cli "$@"' > ~/.local/bin/radar \
    && chmod +x ~/.local/bin/* \
    && echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Set up Git configuration template
RUN git config --global init.defaultBranch main \
    && git config --global pull.rebase false \
    && git config --global core.autocrlf input \
    && git config --global core.editor "code --wait"

# Create common directories
RUN mkdir -p ~/.cache/pip \
    && mkdir -p ~/.local/share \
    && mkdir -p ~/.config

# Keep container running
CMD ["sleep", "infinity"]