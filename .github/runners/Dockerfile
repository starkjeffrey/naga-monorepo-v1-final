# Self-Hosted GitHub Actions Runner
# Based on Ubuntu 22.04 with all required dependencies for Naga monorepo

FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create runner user
RUN useradd -m -s /bin/bash runner

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    postgresql-client \
    redis-tools \
    jq \
    unzip \
    tar \
    sudo \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker (for building images)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.15.0
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install Python UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Add runner to docker group
RUN usermod -aG docker runner

# Allow runner to use sudo without password (needed for some actions)
RUN echo "runner ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to runner user
USER runner
WORKDIR /home/runner

# Install UV for runner user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/runner/.cargo/bin:$PATH"

# Download and extract GitHub Actions runner
ARG RUNNER_VERSION="2.321.0"
RUN curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
    && tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
    && rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Install runner dependencies
RUN sudo ./bin/installdependencies.sh

# Create directories for runner work
RUN mkdir -p /home/runner/_work

# Copy runner configuration script
COPY --chown=runner:runner configure-runner.sh /home/runner/configure-runner.sh
RUN chmod +x /home/runner/configure-runner.sh

# Copy runner startup script
COPY --chown=runner:runner start-runner.sh /home/runner/start-runner.sh
RUN chmod +x /home/runner/start-runner.sh

# Expose the runner work directory as a volume
VOLUME ["/home/runner/_work"]

# Set the entrypoint
ENTRYPOINT ["/home/runner/start-runner.sh"]