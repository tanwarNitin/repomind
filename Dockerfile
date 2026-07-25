# --- Stage 1: Build React Frontend ---
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Production Python Backend & Runner ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy backend requirements and install
COPY backend/pyproject.toml backend/README.md backend/
WORKDIR /app/backend
RUN uv venv && uv sync

# Copy backend application code
COPY backend/ /app/backend/
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
