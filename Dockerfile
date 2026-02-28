# Use official Python image matching user's modern environment (3.12 is stable and modern)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (none needed for now, but good to have)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Render sets this dynamically, but 8000 is default fallback)
EXPOSE 8000

# Command to run the app using uvicorn, reading the PORT environment variable
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"
