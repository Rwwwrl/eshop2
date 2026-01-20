FROM python:3.14

ENV POETRY_VERSION=1.8.3

WORKDIR /app

RUN pip install poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --only main

COPY . .

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "hello_world_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
