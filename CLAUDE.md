# MyEshop

Microservices platform for learning Kubernetes and distributed systems.

## Learning Context

This is a learning project focused on building microservices architecture from scratch. The developer is new to Kubernetes and prioritizes understanding concepts deeply over fast feature delivery. Explanations and guidance are preferred over quick solutions.

## Infrastructure

**Cloud:** Google Cloud Platform (GCP)
**Kubernetes:** GKE (Google Kubernetes Engine)
**Environments:** test-eu (GKE cluster)

**Services:**
- `api_gateway` — public-facing, receives user requests
- `hello_world` — internal service (ClusterIP, no public IP)

**Communication:** `api_gateway` → HTTP → `hello_world`

## Project Structure

```
myeshop/
├── src/services/                 # Microservices (each is independent)
│   ├── api_gateway/
│   │   ├── api_gateway/          # Service code
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── hello_world/
│       ├── hello_world/          # Service code
│       ├── tests/
│       ├── pyproject.toml
│       └── Dockerfile
├── deploy/
│   └── k8s/                      # Kubernetes manifests (Kustomize)
│       ├── api-gateway/
│       │   ├── base/
│       │   └── test-eu/
│       ├── hello-world/
│       │   ├── base/
│       │   └── test-eu/
│       └── infrastructure/       # cert-manager, ingress-nginx
├── docs/
├── justfile                      # Task runner commands
└── pyproject.toml                # Root workspace (dev tools)
```

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

**Type annotations are mandatory.** All functions, methods, and class attributes must have type hints.

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
