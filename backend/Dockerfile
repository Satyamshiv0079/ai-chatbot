# Use a lightweight official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for PyTorch/transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements list
COPY requirements.txt .

# Install dependencies (utilize pip cache)
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose backend service port
EXPOSE 8000

# Set environment variables for clean output logging
ENV PYTHONUNBUFFERED=1

# Start the Flask API
CMD ["python", "api/app.py"]
