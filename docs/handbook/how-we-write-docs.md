# How We Write Documentation

## Purpose

This guide defines how we structure and write documentation following **Domain-Driven Design (DDD)** principles. Documentation should communicate **business meaning**, not just technical implementation.

---

## 1. Core Principles

### Domain
- **Domain = business problem space**
- Contains business concepts, rules, invariants, and behaviors
- Independent of frameworks, databases, or delivery mechanisms
- Must stay free of technical concerns

### Bounded Context
- **Bounded Context = boundary of meaning**
- Defines where a specific domain model and language apply
- Same terms may mean different things in different contexts
- A context is **not** a technical layer and **not** infrastructure

### Application Layer
- **Application = orchestration**
- Defines use cases and workflows
- Coordinates domain objects and/or multiple bounded contexts
- Contains **no business rules**
- May implement cross-context workflows (Saga / Process Manager)

### Infrastructure
- **Infrastructure = technical implementation**
- Persistence, messaging, HTTP, frameworks, cloud, tooling
- Implements interfaces defined by the domain or application
- Must never leak into domain concepts or docs

---

## 2. Documentation Structure

Documentation is split by **intent**, not by technology.

### Root Level (`/docs`)

Shared project-wide documentation that applies across all repositories:

```
/docs
  /application       # Business domain concepts and user journeys
  /architecture      # System design and infrastructure
  /handbook          # How we work (standards, playbooks)
  /system            # Bounded context models (DDD)
```

| Folder | Purpose | Examples |
|--------|---------|----------|
| `/application` | Business domain — entities, relationships, user journeys | concepts.md, user-flows.md |
| `/architecture` | Technical design — infrastructure, deployments, integrations | system-overview.md |
| `/handbook` | Engineering practices — conventions, guides, this file | how-we-write-docs.md |
| `/system` | Bounded context models — domain models for specific API contexts | bounded-contexts/orders/model.md |

Rule:
> `/application` answers **"what does the business do?"**
> `/architecture` answers **"how is the system built?"**
> `/handbook` answers **"how do we work here?"**
> `/system` answers **"how is this bounded context structured?"**

---

## 3. What workflows.md Means

- A **workflow** is a **business process**, not a domain rule
- Workflows often span **multiple bounded contexts**
- Implemented via orchestration (Application Layer, Saga, Process Manager)

A workflow document describes:
- Trigger
- Steps across contexts
- Success path
- Failure and compensation paths
- Ownership of each step

Rules:
- Do **not** place business rules inside workflows
- Do **not** merge bounded context models

---

## 4. Writing Guidelines

- Never treat "context" as "technical representation"
- Never mix infrastructure concerns into domain explanations
- Respect bounded context boundaries
- Prefer **business language** over technical language in system docs
- Place conventions and rules in the handbook, not domain docs

Decision guide:
- **Meaning → Domain**
- **Coordination → Application**
- **Execution → Infrastructure**

---

## 5. Goal

Produce:
- Documentation understandable without tribal knowledge
- Clear separation of **business meaning**, **system behavior**, and **technical execution**
- Code and docs aligned with **DDD best practices**, not framework habits
