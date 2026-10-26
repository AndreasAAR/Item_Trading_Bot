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

name: repo-architect
description: Guides the agent through maintaining required repository architecture maps, codemaps, module documentation, and generated symbol indexes.
---

# Repository Architecture and Code Map Rules

## Purpose
Maintain an accurate, searchable understanding of the repository so that future development tasks can locate existing functionality without repeatedly exploring the entire codebase.

## 1. Required Repository Maps
Maintain the following artifacts, adapting locations to existing repository conventions[cite: 2]:
- `AGENTS.md` — repository navigation, development conventions, and instructions for maintaining maps[cite: 2].  
- `docs/ARCHITECTURE.md` — high-level architecture, module responsibilities, dependency direction, and primary execution flows[cite: 2].  
- `docs/CODEMAP.md` — key files, classes, functions, interfaces, entry points, tests, and extension points[cite: 2].  
- `docs/DECISIONS.md` — significant architectural decisions, constraints, and reasons for non-obvious design choices[cite: 2].  
- `docs/generated/` — machine-generated file inventories, symbol indexes, and dependency information[cite: 2].  
- `README.md` — summarized overview tailored for recruiters, system owners, or tech leads[cite: 2].
- IF (ONLY IF) PROJECT REACHES AROUND A 100+ FILES THEN ADD: Module-level docs (`module_*/docs/readme.md`, `decisions.md`, `codemap.md`, `architecture.md`) to offload details from main docs and prevent bloat[cite: 2].

## 2. Architecture Documentation Requirements
- **ARCHITECTURE.md must describe:** Purpose, subsystems, boundaries, entry points, execution flows, permitted dependency directions, configuration locations, extension points, and build/test/lint commands[cite: 2].
- **CODEMAP.md must provide:** Important directories, key files/classes, feature locations, new functionality placement rules, and test-to-implementation relationships[cite: 2].

## 3. Prefer Generated Facts Over Manual Maintenance
Generate file inventories, symbol listings, and dependency information from current source code whenever practical[cite: 2]. Exclude build outputs, dependency directories, caches, and virtual environments[cite: 2].

## 4. New Modules and Architectural Changes
When introducing a subsystem, module, or public interface:
- Document its responsibility, boundaries, key entry points, and dependencies[cite: 2].
- Identify extension points, link relevant tests, and record significant design decisions[cite: 2].


name: validate-changes
description: Enforces mandatory post-change documentation updates and validation criteria after code modifications.
---

# Post-Change Maintenance & Validation Protocol

## 1. Mandatory Maintenance After Code Changes
After adding, removing, moving, or substantially restructuring code[cite: 2]:
1. Identify which architecture maps and indexes are affected[cite: 2].  
2. Update the relevant curated documentation[cite: 2].  
3. Regenerate any affected machine-generated indexes or graphs[cite: 2].  
4. Verify that documented paths, symbols, dependencies, and commands exist[cite: 2].  
5. Remove references to deleted or renamed components[cite: 2].  
6. Include documentation and index changes in the same commit as the code change when necessary for correctness[cite: 2].

## 2. Validation and Completion Criteria
A task that changes architecture or navigation is not complete until affected maps are updated and validated[cite: 2]. Verify that[cite: 2]:
- Documented file paths resolve[cite: 2].  
- Referenced symbols exist[cite: 2].  
- Generated artifacts match current source[cite: 2].  
- Documentation links resolve[cite: 2].  
- Required generation and validation commands succeed[cite: 2].

*Do not claim that maps have been regenerated or validated unless the corresponding commands have actually been executed[cite: 2].*