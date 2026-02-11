---
name: version
description: Check and update versions across all pyproject.toml files. Use when bumping versions, checking version consistency, or after changing dependencies. Trigger phrases include "check versions", "bump version", "version check", "update version".
user_invocable: true
---

# Version Management

## Pyproject.toml Locations

- **libs:** `src/libs/pyproject.toml`
- **api_gateway:** `src/services/api_gateway/pyproject.toml`
- **hello_world:** `src/services/hello_world/pyproject.toml`
- **wearables:** `src/services/wearables/pyproject.toml`

## Instructions

1. Read the `version` field from every pyproject.toml listed above.
2. Read the `myeshop-libs` dependency version from every service pyproject.toml.
3. Display a table with columns: **Package**, **Version**, **myeshop-libs dep**.
4. Check for issues:
   - If `myeshop-libs` version in libs pyproject.toml is `X.Y.Z`, then every service must have `myeshop-libs = "^X.Y.0"` (matching major.minor). For 0.x versions, `^0.Y.0` only matches `0.Y.*`, so services MUST match the minor version of libs.
   - Flag any service whose `myeshop-libs` constraint does not satisfy the current libs version.
5. If the user asked to **bump**: ask which packages to bump and by what level (patch/minor/major), then apply the changes. After bumping libs, also update all service `myeshop-libs` constraints to match. **Important:** when libs is bumped, every service's `pyproject.toml` changes (the `myeshop-libs` constraint is updated), so CI will require their versions to be bumped too. Therefore, when bumping libs, always bump **all services** as well (at least patch level).
6. After any version edits: run `cd src/libs && poetry lock --no-update` then `cd ../.. && poetry lock --no-update` then `poetry install`.
