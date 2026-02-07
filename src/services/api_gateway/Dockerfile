FROM python:3.14-slim
WORKDIR /app

ENV POETRY_VERSION=1.8.3
RUN pip install poetry==$POETRY_VERSION

ARG REGISTRY_URL
COPY pyproject.toml poetry.lock poetry.toml ./

RUN --mount=type=secret,id=gcp_token \
    poetry source add --priority=supplemental myeshop-python "$REGISTRY_URL" && \
    poetry config http-basic.myeshop-python oauth2accesstoken "$(cat /run/secrets/gcp_token)" && \
    poetry install --no-root --only main

COPY api_gateway/ ./api_gateway/
RUN poetry install --only main

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
