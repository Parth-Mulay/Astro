# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY app /workspace/app
RUN curl -sSLo /workspace/de421.bsp https://jplephem.s3.amazonaws.com/de421.bsp
COPY gunicorn.conf.py /workspace/gunicorn.conf.py

# Create system directories for persistence
RUN mkdir -p /workspace/uploads /workspace/reports /workspace/logs /workspace/backups

# Expose port
EXPOSE 8000

# Run the application using Gunicorn with Uvicorn workers
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
