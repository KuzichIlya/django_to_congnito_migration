FROM python:3.12-slim AS base

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi uvicorn python-dotenv httpx \
    "python-jose[cryptography]" \
    pydantic-settings "sqlalchemy[asyncio]" asyncpg \
    boto3

COPY *.py .
COPY routers/ ./routers/
COPY .env .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
