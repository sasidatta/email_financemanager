# Use Python 3.9 base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (from Bookworm repos)
RUN apt-get update && \ 
    apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 5000

# Run app
CMD ["python", "fetch_emails.py"]