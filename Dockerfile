# WSI Sentinel — FastAPI + React build
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
LABEL maintainer="WSI Data Team"
LABEL description="Returns Intelligence Platform — Williams-Sonoma Inc."

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY generate_data.py .

RUN python generate_data.py

COPY --from=frontend /fe/dist ./frontend/dist

ENV DATA_DIR=data
ENV DATA_REFRESH_INTERVAL_S=3600
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
