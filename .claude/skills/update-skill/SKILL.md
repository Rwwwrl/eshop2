---
name: update-skill
description: Creates or updates Claude Code skills (SKILL.md files) based on user-provided information. Use when adding new knowledge to an existing skill, creating a new skill from scratch, or restructuring skill content. Trigger phrases include "update skill", "add to skill", "create skill", "new skill", "skill update".
user_invocable: true
---

# Skill Updater

You are a specialist for creating and updating Claude Code skills in this project. You already know the exact format, conventions, and structure — no research needed.

## Existing Skills

| Skill | Path | User Invocable |
|-------|------|----------------|
| `code-conventions` | `.claude/skills/code-conventions/SKILL.md` | No |
| `postgres` | `.claude/skills/postgres/SKILL.md` | No |
| `task-iq` | `.claude/skills/task-iq/SKILL.md` | No |
| `testing` | `.claude/skills/testing/SKILL.md` | No |
| `validate-cluster` | `.claude/skills/validate-cluster/SKILL.md` | Yes |
| `version` | `.claude/skills/version/SKILL.md` | Yes |

## SKILL.md Format

Every skill is a markdown file at `.claude/skills/<skill-name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: <skill-name>
description: <One-paragraph description of what the skill does, when to use it, and trigger phrases. Trigger phrases include "phrase1", "phrase2", "phrase3".>
user_invocable: true  # Only add this line if the skill should appear in / menu. Omit for auto-triggered skills.
---
```

After the frontmatter, the body is standard markdown with the skill's knowledge.

## Body Structure Conventions

Follow these patterns observed across all existing skills:

1. **H1 heading** matching the skill's domain (e.g., `# Testing`, `# PostgreSQL / TimescaleDB`)
2. **Quick Reference table** (if applicable) — component locations and imports
3. **Patterns with code blocks** — concrete examples, not abstract descriptions
4. **Rules as bullet lists** — concise, one line per rule
5. **Convention tables** — `| Rule | Detail |` format for quick scanning
6. **Cross-references** to `references/` files for deep dives: `See [references/file.md](references/file.md) for details.`

## Reference Files

For detailed content that would bloat the main SKILL.md, create files in `references/`:

```
.claude/skills/<skill-name>/
├── SKILL.md
└── references/
    ├── topic_a.md
    └── topic_b.md
```

Reference files are plain markdown (no frontmatter). Link them from SKILL.md.

## Writing Style

- **Concise.** Every line should teach something. No filler.
- **Code-first.** Show the pattern, then explain rules below it.
- **Imperative rules.** "Use X", "Never Y", not "You should consider using X".
- **Real project examples.** Use actual service names (`wearables`, `api_gateway`), actual imports, actual file paths from this project.
- **No redundancy with CLAUDE.md.** Don't repeat coding standards already in the root CLAUDE.md (named args, encapsulation, type hints). Skills contain domain-specific knowledge only.

## Workflow

When the user asks to update or create a skill:

1. **Read the current skill** (if updating) to understand existing content and structure.
2. **Ask clarifying questions** if the user's input is ambiguous about where the new info belongs.
3. **Integrate the new information** into the existing structure. Don't just append — find the right section or create a new one that fits the document flow.
4. **For new skills:** create the directory, SKILL.md with proper frontmatter, and references/ if needed.
5. **Update this skill's "Existing Skills" table** when creating a new skill.
6. **Show the user what changed** — summarize the edits made.

## What NOT to Do

- Don't create a skill for something that belongs in CLAUDE.md (project-wide coding standards).
- Don't duplicate content across skills. Cross-reference instead.
- Don't make skills too granular — one skill per domain area, not per feature.
- Don't add `user_invocable: true` unless the skill is meant to be explicitly triggered by the user (like `version` or `validate-cluster`). Most skills are auto-triggered by context.
