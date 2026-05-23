FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so the layer is cached across code changes.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[dev]"

# Migration tooling — copied after install so it does not bust the dependency layer.
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
