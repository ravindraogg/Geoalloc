# Use the openenv-base image which has CUDA and Python 3.12
ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . /app/env
WORKDIR /app/env

# Install Python dependencies globally
# We explicitly install openenv-core[core] which was missing
RUN pip install --no-cache-dir "openenv-core[core]>=0.2.2"
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir unsloth trl huggingface_hub

# Set PYTHONPATH so the server and training script can find the 'env' module
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Expose port 7860 for Hugging Face
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
