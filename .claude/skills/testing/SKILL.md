---
name: testing
description: This skill should be used when the user writes tests, creates test fixtures, or works with pytest and mocking. Use when writing unit tests, integration tests, or debugging test failures. Trigger phrases include "write test", "pytest", "mock", "test case", "fixture".
---

# Testing

## File Structure

Test files mirror source structure inside the service's `tests/` directory. Since each microservice is its own package, there is no `tests_context_name` nesting — tests are already scoped to the service.

- **Source:** `service_name/services/my_service.py`
- **Test:** `tests/tests_services/test_my_service.py`

## Test Naming

```
test_<function_name>_<use_case>
```

Examples:
- `test_get_product_when_product_not_found`
- `test_create_order_when_cart_is_empty`

## Mock Initialization

**Configure mocks completely in `patch()` call:**

```python
# CORRECT
with patch(
    "service_name.context_name.routes.OrderService.create_order",
    return_value=mock_order
) as mock_create:
    response = await async_client.post(...)

# WRONG
with patch(...) as mock_create:
    mock_create.return_value = mock_order  # Don't do this
```

## Test Structure

**Keep `with` blocks minimal - assertions outside:**

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_create_order_success(async_client, test_user, auth_header):
    order_id = str(uuid4())

    with patch(
        "service_name.context_name.routes.OrderService.create_order",
        return_value=None
    ) as mock_create_order:
        response = await async_client.post(
            "api/v1/orders/",
            headers=auth_header,
            json={"product_id": "123", "quantity": 1},
        )

    # Assertions outside with block
    assert response.status_code == status.HTTP_201_CREATED
    mock_create_order.assert_called_once()
```

## Response Validation

**Use Pydantic schemas, not dictionaries:**

```python
response = await async_client.get("api/v1/products/", headers=auth_header)

assert response.status_code == 200
response_content = ProductListSchema(**response.json())  # Validates structure

for product in response_content.items:
    # Work with typed objects
    ...
```

See `references/patterns.md` for more examples.
