# Multi-stage Dockerfile for Wind Forecast Analytics
# Stage 1: Build the React Vite Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /build

# Copy frontend package manifests and install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source code and build production bundle
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Static Server
FROM python:3.12-slim AS runner
WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install minimal backend runtime dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /build/dist ./frontend/dist

# Non-root user for security best practices
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://127.0.0.1:8000/api/health', timeout=3.0); exit(0 if r.status_code == 200 else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
