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
- docs/roadmap.md  - what we are planning to do, and in what order. This is our roadmap, we need to maintain it as we go.
- docs/goal.md - a general idea of our end-goal. 
- Module-level docs (`module_*/docs/readme.md`, `decisions.md`, `codemap.md`, `architecture.md`, roadmap.md, goal.md) to offload details from main docs and prevent bloat[cite: 2].  
- `README.md` — summarized overview tailored for recruiters, system owners, or tech leads[cite: 2].

## 2. Architecture Documentation Requirements
- **ARCHITECTURE.md must describe:** Purpose, subsystems, boundaries, entry points, execution flows, permitted dependency directions, configuration locations, extension points, and build/test/lint commands[cite: 2].
- **CODEMAP.md must provide:** Important directories, key files/classes, feature locations, new functionality placement rules, and test-to-implementation relationships[cite: 2].

## 3. Prefer Generated Facts Over Manual Maintenance
Generate file inventories, symbol listings, and dependency information from current source code whenever practical[cite: 2]. Exclude build outputs, dependency directories, caches, and virtual environments[cite: 2].

## 4. New Modules and Architectural Changes
When introducing a subsystem, module, or public interface:
- Document its responsibility, boundaries, key entry points, and dependencies[cite: 2].
- Identify extension points, link relevant tests, and record significant design decisions[cite: 2].
- Update roadmaps.md and goal.md if needed.