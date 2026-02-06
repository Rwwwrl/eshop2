---
name: code-conventions
description: Detailed code conventions and style rules for MyEshop. Use when writing new code, reviewing code, or when unsure about import style, schema patterns, or code style. Trigger phrases include "convention", "import style", "schema import", "code style", "how to import".
---

# Code Conventions

## Schema Imports

- **Within the same context:** import the module, use `module.ClassName` — makes the origin file obvious at every usage site.
- **From another context:** import the class directly from `schemas/__init__.py` — never reach into internal files like `request_schemas.py` or `dtos.py`.
- **Exporting:** the owning context controls what is public via `schemas/__init__.py` with `__all__`.

See `references/schema_imports.md` for full examples.
