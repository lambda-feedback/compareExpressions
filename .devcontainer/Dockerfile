ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Matches the Python version used by GitHub Actions (test-lint.yml, staging-deploy.yml)
# and the production image (app/Dockerfile), so tests behave the same locally.

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js, required to run the Claude Code CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

# Claude Code refuses --dangerously-skip-permissions as root unless it knows
# it's already inside an isolated sandbox (this container).
ENV IS_SANDBOX=1

# Run `claude` in this container with permission prompts bypassed by default,
# since the container itself (not the CLI) is the safety boundary here. This
# alias only affects the container image, never the host's `claude` config.
RUN echo "alias claude='claude --dangerously-skip-permissions'" >> /etc/bash.bashrc

WORKDIR /workspace

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir pytest flake8

ENV PYTHONPATH=/workspace
