# Dockerfile cho Railway deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for uploads
RUN mkdir -p uploads/teams/members

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port (Railway sẽ tự động set PORT env var)
# Railway thường dùng port 8080, nhưng sẽ set PORT env var
EXPOSE 8080

# Run startup script
CMD ["/app/start.sh"]

