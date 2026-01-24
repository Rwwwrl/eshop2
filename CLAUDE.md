# MyEshop Backend

FastAPI backend for the e-shop platform.

## Learning Context

This is a learning project focused on building microservices architecture from scratch. The developer is new to Kubernetes and prioritizes understanding concepts deeply over fast feature delivery. Explanations and guidance are preferred over quick solutions.

## Current Goal

Microservice architecture with Kubernetes deployment.

**Services:**
- `api_gateway` - receives user requests (public-facing)
- `hello_world` - internal service (no public IP)

**Communication:** `api_gateway` -> HTTP -> `hello_world`

**Python version:** 3.14

**Running Python:** Always use `poetry run python`, not `python` or `python3`

## Linting & Formatting

Uses **ruff** for both linting and formatting (line length: 120):

```bash
poetry run ruff check --fix .
poetry run ruff format .
```

Ruff rules: B, C, E, F, I, W (see `pyproject.toml` for ignored rules)

## Architecture

**Tech-Sliced Architecture:** The codebase follows a context-based architecture where each feature folder groups related functionality around a business capability. Inside each context, code is organized by technical layers.

**Context** = a feature folder inside `app/api/`. Each context groups related functionality (routes, services, models, etc.) around a business capability.

### Project Structure

```
myeshop/
├── app/
│   ├── main.py                   # FastAPI app initialization
│   ├── api/
│   │   └── v1/                   # API version 1
│   │       └── <context>/        # Feature contexts
│   ├── core/                     # Core infrastructure
│   └── tests/                    # Test suite
├── docs/                         # Documentation
├── pyproject.toml                # Dependencies (Poetry)
└── docker-compose.yaml           # Local infrastructure
```

### Context Module Structure

Each context follows this structure:

```
context_module/
├── routes.py                 # API endpoints
├── services/                 # Business logic
├── repositories.py           # Data access
├── models/                   # Database models
├── schemas/
│   ├── request_schemas.py
│   ├── response_schemas.py
│   ├── dtos.py
│   └── nested_models.py
├── dependencies.py           # DI providers
├── exceptions.py             # Domain exceptions
└── utils.py                  # Module utilities
```

## Coding Standards

### Code Comments

**Rarely write comments.** When needed, use `# NOTE @author` for non-obvious context:

```python
# NOTE @sosov: Skip intermediate batches during historical pulls.
```

**When to use NOTE:** non-obvious business logic, external API quirks, important constraints.

**Never comment:** obvious code, variable names, standard operations.

### Default Arguments and Fallbacks

**Think twice before adding defaults.** They can hide bugs by silently accepting missing data.

**Acceptable defaults:** pagination, logging levels, retry counts, optional boolean flags.

**Avoid defaults:** when callers should make explicit choices, or when values are context-dependent.

## Documentation

| Topic                   | Location                                     |
| ----------------------- | -------------------------------------------- |
| System architecture     | [docs/architecture/](docs/architecture/)     |
| Application concepts    | [docs/application/](docs/application/)       |
| Handbook & playbooks    | [docs/handbook/](docs/handbook/)             |
| Bounded contexts        | [docs/system/](docs/system/)                 |

See [docs/handbook/how-we-write-docs.md](docs/handbook/how-we-write-docs.md) for documentation standards.
