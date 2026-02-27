---
name: fastapi
description: Guides FastAPI HTTP service development in MyEshop. Use when creating a new HTTP service, adding endpoints, configuring middleware, setting up lifespan, writing request/response schemas, or structuring FastAPI apps. Trigger phrases include "fastapi", "endpoint", "route", "middleware", "lifespan", "http service", "request schema", "response schema", "health check".
---

# FastAPI

Async HTTP layer using **FastAPI** with **uvicorn**. Each service has an `http/` folder with `main.py` (app setup) and `routes.py` (endpoints). Shared middleware and schemas live in `libs.fastapi_ext`.

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| `BaseRequestSchema` | `libs/fastapi_ext/schemas/base_schemas.py` | `from libs.fastapi_ext.schemas.base_schemas import BaseRequestSchema` |
| `BaseResponseSchema` | `libs/fastapi_ext/schemas/base_schemas.py` | `from libs.fastapi_ext.schemas.base_schemas import BaseResponseSchema` |
| `DTO` | `libs/common/schemas/dto.py` | `from libs.common.schemas.dto import DTO` |
| `BaseAppSettings` | `libs/settings/base_settings.py` | `from libs.settings.base_settings import BaseAppSettings` |
| `SentrySettingsMixin` | `libs/sentry_ext/settings.py` | `from libs.sentry_ext.settings import SentrySettingsMixin` |
| `is_data_sensitive_env()` | `libs/settings/utils.py` | `from libs.settings.utils import is_data_sensitive_env` |
| `setup_logging()` | `libs/logging/config.py` | `from libs.logging.config import setup_logging` |
| `setup_sentry()` | `libs/sentry_ext/config.py` | `from libs.sentry_ext.config import setup_sentry` |
| `setup_fastapi_prometheus()` | `libs/prometheus_ext/utils.py` | `from libs.prometheus_ext.utils import setup_fastapi_prometheus` |
| Middlewares | `libs/fastapi_ext/middlewares/` | `from libs.fastapi_ext.middlewares import ...` |
| `ServiceNameEnum` | `libs/logging/enums.py` | `from libs.logging.enums import ServiceNameEnum` |
| `ProcessTypeEnum` | `libs/logging/enums.py` | `from libs.logging.enums import ProcessTypeEnum` |

## File Structure

```
src/services/<service>/
    <service>/
        settings.py              # Settings singleton (mixin composition)
        utils.py                 # Engine init (if DB needed)
        http/
            __init__.py
            main.py              # FastAPI app, lifespan, middleware
            routes.py            # APIRouter, endpoints
            schemas/
                __init__.py
                request_schemas.py
                response_schemas.py
        schemas/
            dtos.py              # Domain DTOs (shared across protocols)
    env.yaml                     # Local dev settings
```

## App Setup (`http/main.py`)

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from libs.fastapi_ext.middlewares import (
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    RequestResponseLoggingMiddleware,
    SecurityHeadersMiddleware,
    UnhandledExceptionMiddleware,
)
from libs.logging.config import setup_logging
from libs.logging.enums import ProcessTypeEnum, ServiceNameEnum
from libs.prometheus_ext.utils import setup_fastapi_prometheus
from libs.sentry_ext.config import setup_sentry
from libs.settings.utils import is_data_sensitive_env

from <service>.http.routes import router
from <service>.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.<SERVICE>, process_type=ProcessTypeEnum.FASTAPI)
    setup_sentry(settings=settings, release=version("<package-name>"))
    yield


_is_sensitive = is_data_sensitive_env(environment=settings.environment)

app = FastAPI(
    title="<Service Title>",
    version=version("<package-name>"),
    description="<Description>",
    lifespan=lifespan,
    docs_url=None if _is_sensitive else "/docs",
    redoc_url=None if _is_sensitive else "/redoc",
    openapi_url=None if _is_sensitive else "/openapi.json",
)

app.add_middleware(RequestBodyLimitMiddleware, max_body_size=1_048_576)
app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(router=router)
setup_fastapi_prometheus(app=app)
```

Middleware order matters (Starlette processes in reverse of `add_middleware` calls). Execution order:

1. `RequestIdMiddleware` — extracts/generates `X-Request-ID`, sets ContextVar
2. `RequestResponseLoggingMiddleware` — logs request/response, skips `/health` and `/readiness_check`
3. `SecurityHeadersMiddleware` — adds `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`
4. `UnhandledExceptionMiddleware` — catches all exceptions, returns 500 JSON
5. `RequestBodyLimitMiddleware` — rejects oversized requests with 413

Simple services (e.g., `hello_world`) may omit `SecurityHeadersMiddleware` and `RequestBodyLimitMiddleware`.

## Routes (`http/routes.py`)

```python
from fastapi import APIRouter, status
from starlette.responses import Response

from <service>.http.schemas import request_schemas

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}
```

Rules:
- Single `APIRouter()` per service, no prefix or tags
- Include via `app.include_router(router=router)` with keyword arg
- Every service has `/health` (liveness) and `/readiness_check` (readiness)
- Readiness checks infrastructure dependencies (DB, RabbitMQ) if the service has them
- Status codes set in decorator: `@router.post("/webhook", status_code=status.HTTP_201_CREATED)`
- Use `starlette.responses.Response` for bodyless responses: `return Response(status_code=status.HTTP_201_CREATED)`

## Schemas

Three-tier hierarchy: `DTO` → `BaseRequestSchema` / `BaseResponseSchema` → service schemas.

All inherit `frozen=True` and `extra="forbid"` from `DTO`.

```python
# <service>/http/schemas/request_schemas.py
from libs.fastapi_ext.schemas.base_schemas import BaseRequestSchema

class WebhookEventPayload(BaseRequestSchema):
    user_id: int
    biomarker_name: str
    value: float
    timestamp: datetime
```

Domain DTOs extend `DTO` directly (not request/response schemas):

```python
# <service>/schemas/dtos.py
from libs.common.schemas.dto import DTO

class BaseWearableEventDTO(DTO):
    id: int | None
    user_id: int
    biomarker_name: str
```

Schema import convention (from same context, import the module):

```python
from <service>.http.schemas import request_schemas
async def handle_webhook(payload: request_schemas.WebhookEventPayload) -> Response: ...
```

## Status Code Conventions

| Code | Usage |
|------|-------|
| 200 | GET endpoints (default) |
| 201 | Resource creation |
| 202 | Async operations (publish, dispatch) |
| 204 | No content (background task health) |
| 400 | Invalid request headers |
| 413 | Body too large |
| 422 | Pydantic validation (FastAPI default) |
| 500 | Unhandled exceptions (middleware) |
| 503 | Infrastructure health failure |

## Error Handling

No custom exception handlers or `HTTPException`. Errors are handled by middleware:
- `UnhandledExceptionMiddleware` → catches all, returns `{"detail": "Internal Server Error"}` (500)
- `RequestIdMiddleware` → invalid header → `{"detail": "Invalid X-Request-ID header"}` (400)
- `RequestBodyLimitMiddleware` → oversized body → `{"detail": "Request body too large"}` (413)
- Pydantic validation failures → FastAPI default 422

## No `Depends()`

The project does **not** use FastAPI's `Depends()`. Instead:
- **Settings** — module-level singleton: `settings = Settings()`
- **DB sessions** — direct context manager: `async with Session() as session, session.begin():`
- **Request-scoped data** — Python `contextvars` (e.g., `request_id_var`)
- **Engine** — stored on `app.state.sqlmodel_engine`
- **Request bodies** — typed directly in function signatures

## Settings

Mixin composition. See [references/settings_and_deployment.md](references/settings_and_deployment.md) for full details.

```python
from libs.settings.base_settings import BaseAppSettings
from libs.sentry_ext.settings import SentrySettingsMixin

class Settings(SentrySettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(Path(__file__).resolve().parent.parent / "env.yaml"), extra="ignore")

settings = Settings()
```

## Lifespan Patterns

Resources acquired before `yield` (startup), released after `yield` (shutdown).

**With database:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.FASTAPI)
    setup_sentry(settings=settings, release=version("wearables"))
    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)
    app.state.sqlmodel_engine = engine
    yield
    await engine.dispose()
```

**With FastStream broker (publisher-only):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(...)
    setup_sentry(...)
    await faststream_broker.connect()
    yield
    await faststream_broker.stop()
```

## Deployment

See [references/settings_and_deployment.md](references/settings_and_deployment.md) for Dockerfile, K8s deployment, and probe configuration.

Key points:
- Uvicorn command: `poetry run uvicorn <service>.http.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75`
- No `CMD` in Dockerfile — command specified in K8s deployment
- `terminationGracePeriodSeconds: 95`, `preStop: sleep 10`

## Step-by-Step: Adding a New HTTP Service

1. Create service directory: `src/services/<name>/<name>/`
2. Add `settings.py` with mixin composition and `settings = Settings()` singleton
3. Add `env.yaml` with `environment: "dev"` and `log_level: "DEBUG"`
4. Create `http/__init__.py`, `http/main.py`, `http/routes.py`
5. Copy app template from above, update service name and imports
6. Add `/health` and `/readiness_check` endpoints
7. Add `ServiceNameEnum` value in `libs/logging/enums.py`
8. Add `pyproject.toml` with dependencies on `myeshop-libs`
9. Register in root `pyproject.toml`, run `poetry lock --no-update && poetry install`
10. Add `.importlinter` contracts
11. Add Dockerfile (copy from existing service)
12. Add K8s manifests: `deploy/k8s/services/<name>/base/http/deployment.yaml`

## Step-by-Step: Adding an Endpoint

1. Define request schema in `http/schemas/request_schemas.py` (extend `BaseRequestSchema`)
2. Define domain DTO in `schemas/dtos.py` if needed (extend `DTO`)
3. Add route in `http/routes.py` with explicit `status_code`
4. Convert request schema to DTO with keyword arguments (no serializer layer)
5. Use `Session()` context manager for DB operations
6. Return `Response(status_code=...)` for bodyless or `dict` for JSON responses

## Conventions

| Rule | Detail |
|------|--------|
| App creation | Module-level `FastAPI(...)` with conditional docs |
| Lifespan | `@asynccontextmanager`, acquire before `yield`, release after |
| Router | Single `APIRouter()`, no prefix/tags, keyword arg inclusion |
| Middleware | Shared library, consistent stack order across services |
| Health endpoints | `/health` (liveness), `/readiness_check` (readiness with infra checks) |
| Schemas | `DTO` → `BaseRequestSchema`/`BaseResponseSchema`, frozen + extra forbid |
| No `Depends()` | Module singletons, ContextVars, direct context managers |
| Status codes | Named constants from `fastapi.status` |
| Error handling | Middleware-based, no custom exception handlers |
| Prometheus | `setup_fastapi_prometheus(app=app)` after middleware and router |
| Docs | Disabled in production via `is_data_sensitive_env()` |
