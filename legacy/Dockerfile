# ==========================================
# STAGE 1: Build Vite React Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package definition files
COPY frontend/udyog-permit-frontend/package*.json ./

# Install ALL dependencies (including Tailwind Vite plugins)
RUN npm install --include=dev

# Copy the rest of the frontend source files
COPY frontend/udyog-permit-frontend/ ./

# Build production bundle
RUN npm run build

# ==========================================
# STAGE 3: Python Backend & Final Runner
# ==========================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built static frontend files from Stage 1 into FastAPI static dir
COPY --from=frontend-builder /app/frontend/dist ./static

# Render dynamic port binding
ENV PORT=10000
EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT