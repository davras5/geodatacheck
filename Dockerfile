# GeoDataCheck - Dockerfile for Fly.io
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy workflows (needed for GWR enricher)
COPY workflows/ ./workflows/

# Copy frontend (single HTML file)
COPY index.html .

# Copy assets (logos, icons)
COPY assets/ ./assets/

# Set working directory to backend for running the app
WORKDIR /app/backend

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
