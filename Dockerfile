FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/tmp/hf \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
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

COPY --chown=user:user . .

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
