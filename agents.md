# Repository Agent Guidelines

## 1. Repository Exploration Protocol
Before implementing any feature or modification:
1. Consult the relevant architecture map (`docs/ARCHITECTURE.md`) and codemap (`docs/CODEMAP.md`).
2. Search for existing implementations, related symbols, callers, and tests.
3. Inspect the smallest set of files sufficient to understand the change.
4. Reuse established interfaces, abstractions, and conventions.

## 2. Source of Truth
Treat the implementation as authoritative unless the task explicitly changes the architecture. Do not modify source code merely to make documentation appear consistent with an incorrect description.

> **Need to build modules or update maps?** Invoke the `repo-architect` or `validate-changes` skills for full maintenance protocols.