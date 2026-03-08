FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

ENV PYTHONPATH=/app

# Default command — overridden per service in render.yaml
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
