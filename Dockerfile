# Unified Dockerfile for SecureHeal Arena (Environment + Training)
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    curl \
    libgoogle-perftools-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install unified requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port for the environment server
EXPOSE 8000

# Entrypoint: Start the environment server AND the training loop
# This allows the reward function to talk to localhost:8000
CMD uvicorn secureheal_arena.server.app:app --host 0.0.0.0 --port 8000 & \
    python3 training/train.py
