# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y \
    # Required for Pillow (image processing)
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    # Required for pytesseract (OCR)
    tesseract-ocr \
    tesseract-ocr-eng \
    # Required for some Python packages
    build-essential \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# Copy the entire backend code
COPY . .

# Create directory for uploaded files (if it doesn't exist)
RUN mkdir -p /app/uploaded_files

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]