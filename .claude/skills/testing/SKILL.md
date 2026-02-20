---
name: testing
description: Guides pytest test writing for MyEshop services. Covers async test patterns, httpx client fixtures, database integration tests, mock patterns, and conftest structure. Use when writing tests, creating fixtures, debugging test failures, or setting up test infrastructure. Trigger phrases include "write test", "pytest", "mock", "test case", "fixture", "conftest", "integration test".
---

# Testing

## Two Test Patterns

### Unit Tests (no DB)

For libs, api_gateway, hello_world. Function-scoped fixtures, self-contained.

```python
@pytest.mark.asyncio
async def test_debug_error_returns_500(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/debug/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
```

### Integration Tests (with DB)

For services with PostgreSQL. Session-scoped fixtures, shared DB infrastructure.

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_valid_payload(async_client: AsyncClient) -> None:
    payload = {
        "user_id": 1,
        "biomarker_name": "heart_rate",
        "value": 72.5,
        "timestamp": "2025-02-11T10:00:00Z",
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 201

    async with Session() as session, session.begin():
        result = await session.execute(select(WearableEvent))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].user_id == 1
```

## Test Naming

```
test_<function_name>_when_<condition>
```

Examples: `test_get_product_when_product_not_found`, `test_handle_webhook_when_missing_required_field`

## File Structure

Tests mirror source structure inside `tests/`. No `__init__.py` files (importlib mode).

```
src/services/wearables/
├── wearables/
│   ├── routes.py
│   └── models.py
└── tests/
    ├── conftest.py
    └── test_routes.py
```

## Async Configuration

- `asyncio_default_fixture_loop_scope = "session"` in pytest config
- `@pytest.mark.asyncio` for unit tests (uses default session scope)
- `@pytest.mark.asyncio(loop_scope="session")` explicit for DB integration tests
- `@pytest_asyncio.fixture()` for async fixtures (not `@pytest.fixture`)
- `--import-mode=importlib` — no `__init__.py` in test dirs

## conftest.py Templates

See [references/conftest_templates.md](references/conftest_templates.md) for unit test and DB integration conftest patterns, plus representative test examples.

## Mock Patterns

See [references/mocks.md](references/mocks.md) for patch, AsyncMock, side_effect, and assertion patterns.

## DB Test Infrastructure

For services with PostgreSQL, the shared plugin `libs.tests_ext.sqlmodel_fixtures` (loaded via `-p` flag) provides:

1. **`sqlmodel_engine`** (session scope) — creates/drops a `test` database, runs `create_all`
2. **`_clear_sqlmodel_tables`** (autouse, function scope) — TRUNCATEs tables after each test

Services must provide two fixtures in their conftest:
- `settings` (session scope) — returns `PostgresSettingsMixin`-based settings
- `autocleared_sqlmodel_tables` (session scope) — returns `list[type[BaseSqlModel]]`

Add `-p libs.tests_ext.sqlmodel_fixtures` to `addopts` in the service's `pytest.ini`.

## Response Validation

Use Pydantic schemas for response validation, not raw dicts:

```python
response = await async_client.get(url="/api/v1/products/", headers=auth_header)
assert response.status_code == 200
response_content = ProductListSchema(**response.json())
```

## Conventions

| Rule | Detail |
|------|--------|
| Return types | Always annotate (`-> None`, `-> AsyncGenerator[AsyncClient]`) |
| Keyword args | Always use (`url=`, `json=`, `headers=`, `router=`) |
| Internal fixtures | Prefix with `_` (e.g., `_clear_sqlmodel_tables`) |
| Line length | E501 ignored in tests (`**/tests/**/*`) |
| DB assertions | Use `Session()` directly, not through the API |
| Fixture scope | Function for unit tests, session for DB integration |
