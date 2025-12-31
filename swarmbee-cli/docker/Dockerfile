# SwarmBee Worker Container
# MONAI + PyTorch + CUDA for medical AI inference
#
# Build: docker build -t swarmos/bee-worker:latest .
# Run: (via swarmbee CLI)

FROM nvcr.io/nvidia/pytorch:24.01-py3

LABEL maintainer="SudoHash LLC <dev@sudohash.com>"
LABEL description="SwarmBee Worker - Medical AI Inference"
LABEL version="1.0.0"

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install MONAI with all optional dependencies
RUN pip install --no-cache-dir \
    "monai[all]>=1.3.0" \
    nibabel \
    pydicom \
    pillow \
    reportlab \
    httpx \
    redis \
    python-multipart

# Create directories
RUN mkdir -p /app /data /models /logs /outputs

WORKDIR /app

# Copy worker code
COPY worker/ /app/

# Create non-root user
RUN useradd -m -u 1000 swarmbee && \
    chown -R swarmbee:swarmbee /app /data /models /logs /outputs

USER swarmbee

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose worker API port
EXPOSE 8080

# Start worker
CMD ["python", "-m", "worker.main"]
