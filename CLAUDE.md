# MyEshop

Microservices platform for learning Kubernetes and distributed systems.

## Learning Context

This is a learning project focused on building microservices architecture from scratch. The developer is new to Kubernetes and prioritizes understanding concepts deeply over fast feature delivery. Explanations and guidance are preferred over quick solutions.

## Infrastructure

**Cloud:** Google Cloud Platform (GCP)
**Kubernetes:** GKE (Google Kubernetes Engine)
**Environments:** test-eu (GKE cluster)
**Ingress Controller:** NGINX Inc (`nginx-stable/nginx-ingress` Helm chart) — test-eu only
**TLS:** cert-manager with Let's Encrypt

## Service Internal Architecture

Every microservice follows **vertical slice architecture**. Code is organized by **context** (feature/domain area), not by technical layer. Each context groups related functionality around a business capability, with technical layers inside.

**Context** = a feature folder inside the service package. A context is a boundary of meaning (DDD Bounded Context) — it owns its routes, services, models, schemas, and data access.

### Context Module Structure

```
context_name/
    routes.py                 # API endpoints (FastAPI router)
    services.py               # Business logic (or services/ directory for multiple)
    repositories.py           # Data access layer
    models.py                 # Database models (or models/ directory)
    schemas/
        request_schemas.py    # Pydantic request validation schemas
        response_schemas.py   # Pydantic response schemas
        dtos.py               # Data Transfer Objects (internal, between layers)
        nested_models.py      # Embedded sub-models for documents/DTOs
    serializers.py            # DTO → response schema conversion
    exceptions.py             # Domain-specific exceptions
```

Additional common files (add as needed): `enums.py`, `utils.py`, `settings.py`.

Not every context needs every file. Smaller contexts may only have `routes.py`, `services.py`, and `schemas/`. Add files as the context grows.

### Layer Dependency Direction

```
routes.py  →  services.py  →  repositories.py  →  models.py
    |              |                  |
    v              v                  v
schemas/        schemas/           schemas/
  request         dtos               dtos
  response                           nested_models
    |
    v
serializers.py  (DTO → response_schemas)
```

Routes depend on services, services depend on repositories, repositories depend on models. Schemas are used across layers. Never import routes from services or repositories.

### Shared Library

`src/libs/` is a separate Poetry package (`myeshop-libs`) with shared code used across all services. Services depend on it via path dependency: `myeshop-libs = { path = "../../libs", develop = true }`


## Development

**Python version:** 3.14

**Running Python:** Always use `poetry run python`, not `python` or `python3`

**Adding dependencies:** Use `poetry add` command, never edit `pyproject.toml` directly:

```bash
poetry add fastapi              # Add main dependency
poetry add --group dev pytest   # Add dev dependency
```

**Linting & Formatting:** Uses **ruff** (line length: 120):

```bash
poetry run ruff check --fix .
poetry run ruff format .
```

**Task runner:** Uses `just` (see `justfile` for available commands).

## Coding Standards

- **Async first.** Every microservice is async. Use `async def` for endpoints, service methods, and I/O operations. Sync code is the exception, not the rule.
- **Pydantic for data models.** Use Pydantic (`BaseModel`) when defining data containers, schemas, configs, or anything that benefits from validation and serialization. Plain classes are fine when Pydantic adds no value — not everything needs to be a Pydantic model.
- **Type annotations are mandatory.** All functions, methods, and class attributes must have type hints.
- **Enum naming.** All enum classes must use the `Enum` suffix (e.g., `EnvironmentEnum`, `LogLevelEnum`, `OrderStatusEnum`).

### Named Arguments

**Always use keyword arguments.** Never use positional arguments when calling functions or methods.

```python
# Bad - positional arguments
user = create_user("John", "john@example.com", True)

# Good - keyword arguments
user = create_user(name="John", email="john@example.com", is_active=True)
```

**Exception:** Single-argument calls where the meaning is obvious (e.g., `len(items)`, `str(value)`).

### Code Comments

**Rarely write comments.** When needed, use `# NOTE @author` for non-obvious context:

```python
# NOTE @sosov: Skip intermediate batches during historical pulls.
```

**When to use NOTE:** non-obvious business logic, external API quirks, important constraints.

**Never comment:** obvious code, variable names, standard operations.

### Default Arguments and Fallbacks

**Think twice before adding defaults.** They can hide bugs by silently accepting missing data.

```python
# Bad - caller should explicitly decide
def send_notification(user: User, priority: str = "normal"): ...

# Good - well-established convention
def paginate(items: list, page: int = 1, page_size: int = 20): ...
```

**Acceptable defaults:** pagination, logging levels, retry counts, optional boolean flags.

**Avoid defaults:** when callers should make explicit choices, or when values are context-dependent.

**Avoid fallbacks:** Don't use `value or default_value` patterns to silently handle missing data. If a value is required, let it fail explicitly rather than substituting a fallback that hides the real problem.

**New fields should be required by default.** When adding fields to models, schemas, or dataclasses, make them required unless there's a clear reason for optionality. Don't preemptively add `Optional`, `None` defaults, or `= Field(default=...)` just to avoid migration issues or "be safe."

```python
# Bad - making fields optional "just in case"
class User:
    name: str
    email: str
    role: str | None = None  # Why optional? Every user needs a role.

# Good - required unless truly optional
class User:
    name: str
    email: str
    role: str  # Required. Caller must provide it.
```
