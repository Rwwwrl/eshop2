FROM python:3.14 AS base
ENV POETRY_VERSION=1.8.3
WORKDIR /app
RUN pip install poetry==$POETRY_VERSION
COPY pyproject.toml poetry.lock poetry.toml ./
COPY hello_world_service/ ./hello_world_service/
RUN poetry install --no-root --only main

FROM base AS ci
COPY tests/ ./tests/
COPY pytest.ini ./
RUN poetry install --no-root --only dev
CMD ["poetry", "run", "pytest"]

FROM base AS production
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "hello_world_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
