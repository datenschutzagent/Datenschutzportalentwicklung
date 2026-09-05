FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run uvicorn. --proxy-headers makes uvicorn honour X-Forwarded-For/-Proto from the reverse proxy,
# but only from hosts listed in FORWARDED_ALLOW_IPS (env, default 127.0.0.1). Without this the
# per-IP rate limiter sees the Traefik container IP for every request.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
