# Build context MUST be the repository root (parent of `backend/`), e.g.:
#   docker build -f backend/Dockerfile -t fiatpandas-backend .
# With docker compose, `docker-compose.yml` sets `context: .` and `dockerfile: backend/Dockerfile`.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface/hub

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/
COPY docs/prompts/system_prompt.txt /app/docs/prompts/system_prompt.txt

# Ten sam port co domyślny `VITE_API_BASE_URL` / mockApi (8001) — mniej zamieszania między Dockerem a lokalnym uvicorn.
EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
