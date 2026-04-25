# training/Dockerfile.training
# Optimized for Hugging Face Spaces GPU (A10G / L4)

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
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (Unsloth + TRL)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir \
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" \
    trl \
    peft \
    accelerate \
    bitsandbytes \
    datasets \
    transformers \
    fastapi \
    uvicorn \
    wandb \
    openenv-core

# Copy the project files
COPY . .

# Expose port for optional monitoring UI
EXPOSE 7860

# Command to run:
# 1. Start the environment server in the background
# 2. Start the training script
CMD uvicorn secureheal_arena.server.app:app --host 0.0.0.0 --port 8000 & \
    python3 training/train.py
