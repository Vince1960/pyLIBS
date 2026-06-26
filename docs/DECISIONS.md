# pyLIBS Design Decisions

This document records important architectural and implementation decisions.

Only decisions that affect the future evolution of the project should be recorded.

------------------------------------------------------------

## 2026-06-26

### Git adopted

Decision

Use Git as the official version control system.

Reason

Allow traceability, rollback and controlled development.

------------------------------------------------------------

## 2026-06-26

### Codex workflow

Decision

Use OpenAI Codex as the implementation assistant.

Reason

Automate repetitive coding tasks while preserving project architecture.

------------------------------------------------------------

## 2026-06-26

### Historical compatibility

Decision

Maintain compatibility with:

- LIBS.db
- Stark.db
- pyLIBS.ini
- historical template format

Reason

Allow existing users to migrate without changing data.

------------------------------------------------------------

## 2026-06-26

### Development strategy

Decision

Behaviour first.

Refactoring later.

Reason

Functional compatibility has higher priority than code elegance.

------------------------------------------------------------

## 2026-06-26

### Functional specification

Decision

The LIBS++ User Manual is the historical functional specification.

When differences exist:

- preserve newer behaviour unless explicitly requested;
- document discrepancies.

