# Accept base image as build argument for CI/CD flexibility
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE}

# Install dependencies
COPY secureheal_arena/server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy environment code
COPY src/openenv/core/ /app/src/openenv/core/
COPY secureheal_arena/ /app/secureheal_arena/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["uvicorn", "secureheal_arena.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
