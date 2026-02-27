# Settings and Deployment Reference

## Settings Mixins

`BaseAppSettings` inherits from `LoggingSettingsMixin` and `BaseSettings`. Uses `SettingsConfigDict(yaml_file="env.yaml", extra="ignore")`. Overrides `settings_customise_sources()` to conditionally load YAML only if the file exists. In K8s, settings come from env vars; locally, `env.yaml` provides values.

| Mixin | Fields |
|-------|--------|
| `LoggingSettingsMixin` | `environment: EnvironmentEnum`, `log_level` (default: `INFO`) |
| `PostgresSettingsMixin` | `postgres_direct_db_url`, `postgres_pooler_db_url` (optional) |
| `SentrySettingsMixin` | `sentry_dsn`, `sentry_send_pii`, `sentry_traces_sample_rate` — required for stand envs, forbidden otherwise |
| `FaststreamSettingsMixin` | `faststream_rabbitmq_url`, `faststream_graceful_timeout` (default: 65.0) |
| `TaskiqSettingsMixin` | `taskiq_redis_url`, `taskiq_metrics_port` (default: 9090), `taskiq_health_port` (default: 8081) |

Services compose only the mixins they need:

```python
# Simple service (hello_world, api_gateway)
class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")

# DB + background tasks service (wearables)
class Settings(SentrySettingsMixin, PostgresSettingsMixin, TaskiqSettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

Always end with `settings = Settings()` singleton.

## Environment Helpers

`is_stand_env(environment)` — returns `True` for `TEST` and `PROD`
`is_data_sensitive_env(environment)` — returns `True` only for `PROD`

`EnvironmentEnum` values: `DEV`, `TEST`, `PROD`, `CICD`

## Local `env.yaml`

```yaml
environment: "dev"
log_level: "DEBUG"
faststream_rabbitmq_url: "amqp://guest:guest@localhost:15672/"
# Add more settings as needed
```

## Dockerfile Pattern

All services share this structure:

```dockerfile
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
COPY <service_name>/ ./<service_name>/
RUN poetry install --only main
EXPOSE 8000
```

- No `CMD` — command specified per-deployment in K8s manifests
- Two-stage `poetry install` for dependency caching
- DB services additionally copy `alembic.ini` and `migrations/`

## K8s Deployment

```yaml
command: ["poetry", "run", "uvicorn", "<service>.http.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
```

Probe configuration (all services):

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 45
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet:
    path: /readiness_check
    port: 8000
  initialDelaySeconds: 3
  periodSeconds: 5
  failureThreshold: 3
```

Other deployment details:
- `terminationGracePeriodSeconds: 95`
- `preStop` lifecycle hook: `sleep 10` (gives NGINX time to deregister pod)
- Resources: 50m/128Mi requests, 200m/256Mi limits

## Logging

Called in lifespan:

```python
setup_logging(settings=settings, service_name=ServiceNameEnum.<SERVICE>, process_type=ProcessTypeEnum.FASTAPI)
```

| Environment | Formatter | Output |
|-------------|-----------|--------|
| `TEST`, `PROD` | `GKEJsonFormatter` | Structured JSON (GCP Cloud Logging compatible) |
| `DEV`, `CICD` | `DevFormatter` | `HH:MM:SS \| LEVEL \| eshop \| service/process_type \| request_id \| logger \| message` |

Suppressed loggers: `uvicorn.access`, `httpx`, `httpcore` (set to WARNING).

`ProcessTypeEnum` values: `FASTAPI`, `TASKIQ`, `FASTSTREAM`

## Middleware Details

### RequestBodyLimitMiddleware

Pure ASGI middleware (not `BaseHTTPMiddleware`). Checks `Content-Length` header upfront and streaming body size. Returns 413 with `{"detail": "Request body too large"}`. Default limit: 1MB (`1_048_576`).

### RequestIdMiddleware

Extracts or generates `X-Request-ID` header. Sets `request_id_var` ContextVar. Validates: max 256 chars, printable ASCII only. Returns 400 for invalid headers.

### RequestResponseLoggingMiddleware

Logs request/response with sanitized headers (whitelist: `content-type`, `user-agent`, `x-request-id`). Skips `/health` and `/readiness_check`. Caps logged body at 10,000 characters.

### SecurityHeadersMiddleware

Adds `X-Content-Type-Options: nosniff` and `Strict-Transport-Security` headers.

### UnhandledExceptionMiddleware

Catches all unhandled exceptions. Logs with structured extras (`exception_type`, `exception_message`, `http_method`, `http_url`). Returns `{"detail": "Internal Server Error"}` (500). Never exposes internals to client.

## Test Fixture Pattern

```python
@pytest.fixture(scope="session")
def fastapi_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(UnhandledExceptionMiddleware)
    app.include_router(router=router)
    return app

@pytest_asyncio.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
```

Test apps are minimal — no lifespan, no Sentry, no logging. Only include middleware needed for tests (typically `UnhandledExceptionMiddleware`). Session-scoped app and client.

For DB services, the `fastapi_app` fixture depends on `sqlmodel_engine` to bind `Session` before yielding.
