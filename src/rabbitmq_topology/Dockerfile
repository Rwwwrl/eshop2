FROM python:3.14-slim
WORKDIR /app

ENV POETRY_VERSION=1.8.3
RUN pip install poetry==$POETRY_VERSION

ARG REGISTRY_URL
COPY pyproject.toml ./

RUN --mount=type=secret,id=gcp_token \
    poetry source add --priority=supplemental myeshop-python "$REGISTRY_URL" && \
    poetry config http-basic.myeshop-python oauth2accesstoken "$(cat /run/secrets/gcp_token)" && \
    poetry install --no-root --only main

COPY rabbitmq_topology/ ./rabbitmq_topology/
RUN poetry install --only main
