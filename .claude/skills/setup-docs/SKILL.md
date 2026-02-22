---
name: setup-docs
description: Updates environment setup documentation (setup-env.md) and the GKE bootstrap script (gke-up.sh). Use when infrastructure setup changes, new tools are added, cluster bootstrap steps change, or new environments are created. Trigger phrases include "update setup docs", "setup documentation", "gke-up changes", "environment setup", "setup-env".
user_invocable: true
---

# Update Setup Documentation

## Target Files

| File | Purpose |
|------|---------|
| `documentation/setup-env.md` | Step-by-step environment setup for developers |
| `scripts/gke-up.sh` | GKE cluster bootstrap script |

## Workflow

1. **Read both files in full** before making any changes.
2. **Identify what changed** based on the user's request.
3. **Edit only affected sections.** Do not touch unrelated sections.
4. **Cross-reference.** If `gke-up.sh` changed, verify `setup-env.md` still matches. If `setup-env.md` changed, verify it reflects what `gke-up.sh` actually does.
5. **Show what changed.** After editing, list: file, section heading, what was added/removed/modified.

## Writing Style

- **Script/CLI first.** Document `gcloud` commands, not Console UI click-through steps. If a script or CLI command exists for an action, never document the GUI alternative.
- Numbered steps. Each step = one action: "Run X", "Create Y", "Verify Z".
- No prose paragraphs between steps.
- No "why" explanations. Never explain what a tool is or why a step exists.
- No suggestions, alternatives, or "you could also" branches. One path.
- No filler phrases: "Make sure to", "It's important to", "Note that", "Simply", "Please".
- No assumptions about environments, tools, or services not already in the target files.
- Commands use exact paths and real project values — never `<your-value>` placeholders for things already known.
- Use `<PLACEHOLDER>` only for values that genuinely vary per setup (project ID, IP, region).
- Tables for structured data (variables, secrets, config values).
- Fenced code blocks with `bash` language tag for shell commands.
- File paths relative to project root, in backticks.

## Anti-Patterns (Never Do These)

- Do not add "Troubleshooting" or "FAQ" sections.
- Do not add prerequisites not already in the file unless the user provides them.
- Do not explain what a tool is (e.g., "Helm is a package manager for Kubernetes").
- Do not reformat or reorganize sections the user did not ask to change.
- Do not add commentary like "This was added because..." or "In the future, you might want to..."
- Do not invent steps. If unsure whether a step exists, ask.
- Do not add notes, tips, warnings, or suggestions unless the user explicitly provides them.
- Do not duplicate information — if something is already documented in one section, reference it, don't repeat it.
- Do not document Console UI (click-through) steps when a `gcloud` CLI or script alternative exists.

## Section Structure Convention

`setup-env.md` follows this pattern:
- `## Section Title` for major topics
- `### N. Step title` for numbered steps within a section
- Tables for environment variables, secrets, and config
- Code blocks for commands

When adding new sections, follow the existing heading hierarchy and numbering.
