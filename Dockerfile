FROM python:3.11-slim

# Node.js 20 is required by Reflex to compile the frontend.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        unzip \
        libpq5 \
        ghostscript \
        libsm6 \
        libxext6 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cached unless requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full source.
COPY . .

RUN chmod +x docker-entrypoint.sh

# Reflex frontend port (3000) and backend port (8000).
EXPOSE 3000 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
