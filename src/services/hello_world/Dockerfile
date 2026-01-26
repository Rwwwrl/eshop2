FROM python:3.14-slim
WORKDIR /app

ENV POETRY_VERSION=1.8.3
RUN pip install poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --no-root --only main

COPY hello_world/ ./hello_world/
COPY VERSION ./

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "hello_world.main:app", "--host", "0.0.0.0", "--port", "8000"]
