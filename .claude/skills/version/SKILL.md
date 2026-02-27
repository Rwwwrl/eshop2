---
name: version
description: Check and update versions across all pyproject.toml files. Use when bumping versions, checking version consistency, or after changing dependencies. Trigger phrases include "check versions", "bump version", "version check", "update version".
user_invocable: true
---

# Version Management

## Pyproject.toml Locations

### Shared Packages

| Package | Path |
|---------|------|
| `myeshop-libs` | `src/libs/pyproject.toml` |
| `myeshop-messaging-contracts` | `src/messaging_contracts/pyproject.toml` |
| `myeshop-rabbitmq-topology` | `src/rabbitmq_topology/pyproject.toml` |

### Services

| Service | Path |
|---------|------|
| `api_gateway` | `src/services/api_gateway/pyproject.toml` |
| `hello_world` | `src/services/hello_world/pyproject.toml` |
| `wearables` | `src/services/wearables/pyproject.toml` |

## Dependency Graph

```
services (api_gateway, hello_world, wearables)
  ├── myeshop-libs
  │     ├── myeshop-messaging-contracts
  │     └── myeshop-rabbitmq-topology
  ├── myeshop-messaging-contracts
  └── myeshop-rabbitmq-topology
        └── myeshop-messaging-contracts
```

All shared packages are path dependencies in the root `pyproject.toml`. Services depend on all three. `myeshop-libs` depends on `myeshop-messaging-contracts` and `myeshop-rabbitmq-topology`. `myeshop-rabbitmq-topology` depends on `myeshop-messaging-contracts`.

## Instructions

1. Read the `version` field from every pyproject.toml listed above.
2. Read dependency versions (`myeshop-libs`, `myeshop-messaging-contracts`, `myeshop-rabbitmq-topology`) from every consumer pyproject.toml.
3. Display a table with columns: **Package**, **Version**, **myeshop-libs dep**, **myeshop-messaging-contracts dep**, **myeshop-rabbitmq-topology dep**.
4. Check for issues:
   - For 0.x versions, `^0.Y.0` only matches `0.Y.*`, so consumers MUST match the minor version of the shared package.
   - If `myeshop-libs` version is `0.Y.Z`, then every consumer (services) must have `myeshop-libs = "^0.Y.0"`.
   - If `myeshop-messaging-contracts` version is `0.Y.Z`, then every consumer (services, libs, rabbitmq_topology) must have `myeshop-messaging-contracts = "^0.Y.0"`.
   - If `myeshop-rabbitmq-topology` version is `0.Y.Z`, then every consumer (services, libs) must have `myeshop-rabbitmq-topology = "^0.Y.0"`.
   - Flag any consumer whose constraint does not satisfy the current shared package version.
5. If the user asked to **bump**: ask which packages to bump and by what level (patch/minor/major), then apply the changes. After bumping a shared package, check whether the new version is still covered by existing consumer constraints. If it is (e.g., `0.9.0` → `0.9.1` and consumers have `^0.9.0`), no consumer changes needed. If it is **not** (e.g., `0.9.x` → `0.10.0` and consumers have `^0.9.0`), update all consumer constraints to match — and since their `pyproject.toml` files change, bump all consumer versions too (at least patch level).
6. After any version edits: run `poetry lock --no-update` then `poetry install` from the project root.
