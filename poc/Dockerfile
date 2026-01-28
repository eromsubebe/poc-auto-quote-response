# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY poc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY poc/ ./poc/

# Create data directories
RUN mkdir -p poc_data/emails poc_data/attachments

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000
# Run with uvicorn
CMD ["uvicorn", "poc.main:app", "--host", "0.0.0.0", "--port", "8000"]
