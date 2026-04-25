FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire codebase into the container
# This includes the `space/` directory and the root `app.py` 
# along with `secureheal_arena/` since the UI imports it.
COPY . .

# Expose the default HF Spaces port
EXPOSE 7860

# Run the FastAPI server in the space/ folder
CMD ["uvicorn", "space.app:app", "--host", "0.0.0.0", "--port", "7860"]
