FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/user/hf-cache \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user && \
    mkdir -p /home/user/hf-cache /tmp/p1 /tmp/p2 && \
    chown -R user:user /home/user/hf-cache /tmp/p1 /tmp/p2 && \
    chmod 777 /tmp/p1 /tmp/p2

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

COPY --chown=user:user requirements.txt .

RUN --mount=type=secret,id=GITHUB_TOKEN,required=false,uid=1000 \
    if [ -f /run/secrets/GITHUB_TOKEN ]; then \
        TOKEN=$(cat /run/secrets/GITHUB_TOKEN); \
        if [ -n "$TOKEN" ]; then \
            git config --global url."https://${TOKEN}@github.com/".insteadOf "https://github.com/"; \
        fi; \
    fi && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    git config --global --unset-all url."https://${TOKEN}@github.com/".insteadOf 2>/dev/null || true

# Copy registry and prefetch script before app code for optimal layer caching
COPY --chown=user:user registry.py prefetch.py ./

# Run build-time model prefetch to bake weights into HF_HOME
RUN --mount=type=secret,id=GITHUB_TOKEN,required=false,uid=1000 \
    python prefetch.py

# Set offline mode for runtime only
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Copy application code
COPY --chown=user:user . .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
