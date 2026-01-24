# STAGE: base
FROM python:3.14 AS base

ENV POETRY_VERSION=1.8.3
WORKDIR /app
RUN pip install poetry==$POETRY_VERSION
COPY pyproject.toml poetry.lock ./
COPY . .

# STAGE: ci
FROM base AS ci
RUN poetry install --no-root --only dev

# STAGE: production (default - last stage)
FROM base AS production
RUN poetry install --no-root --only main
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
