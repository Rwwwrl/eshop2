Create a commit for staged changes.

## Rules

**Format:** `[scope] <type> <context> <description>`

**Scope** (where changes were made):
- `[root]` - root-level files (workflows, configs)
- `[* services]` - changes across all services
- `[<service-name>]` - specific service, e.g. `[api-gateway]`, `[hello-world]`

**Type** (what kind of change):
- `feat` - new functionality
- `fix` - bug fix
- `chore` - formatting, docs, refactoring

**Context:** Main file or area affected (e.g. `routes.py`, `Dockerfile`, `VERSION`)

**Description:** One line, concise. No detailed explanations.

**Do not include** `Co-Authored-By` lines in commits.

**Examples:**
```
[api-gateway] feat routes.py added /health and /readiness endpoints
[* services] chore Dockerfile.ci switched to python:3.14-slim
[root] fix on-pull-request.yaml added missing permissions
[hello-world] fix main.py corrected startup error handling
```

## Steps

1. Run `git status` and `git diff --staged` to understand what is being committed.
2. If nothing is staged, stage the relevant changed files (prefer specific files over `git add .`).
3. Draft a commit message following the format above.
4. Create the commit.
