Repository Architecture and Code Map Rules
Purpose
Maintain an accurate, searchable understanding of the repository so that future development tasks can locate existing functionality without repeatedly exploring the entire codebase.
Architecture documentation and navigation indexes are part of the project, not optional deliverables.
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

2. Mandatory maintenance after code changes
After adding, removing, moving, or substantially restructuring code:
Identify which architecture maps and indexes are affected.
Update the relevant curated documentation.
Regenerate any affected machine-generated indexes or graphs.
Verify that documented paths, symbols, dependencies, and commands exist.
Remove references to deleted or renamed components.
Include documentation and index changes in the same commit as the code change when they are necessary for correctness.
Do not update unrelated documentation for trivial changes that do not affect navigation or architecture.
3. Architecture documentation requirements
ARCHITECTURE.md must describe:
The project's purpose and major subsystems.
The responsibility and boundaries of each subsystem.
The main entry points and execution flows.
Important dependencies and the permitted direction of dependencies.
Where configuration, shared types, interfaces, persistence, external integrations, and tests belong.
The existing extension points for adding features.
The commands required to build, test, lint, and validate the project.
CODEMAP.md must provide actionable navigation guidance:
Important directories and their responsibilities.
Key files, classes, functions, and interfaces.
Where representative existing features are implemented.
Where new functionality of each major type should be added.
The relationship between implementation files and their tests.
Links to more detailed documentation where necessary.
Prefer specific paths and symbol names over vague descriptions.
4. Prefer generated facts over manually maintained facts
Generate file inventories, symbol listings, and dependency information from the current source code whenever practical.
Do not manually maintain information that can be reliably extracted from the repository.
Generated artifacts must be reproducible, and their generation process must be documented. Exclude build outputs, dependency directories, caches, virtual environments, and other irrelevant files.
Do not treat a generated dependency graph as proof of runtime behavior when dependencies are dynamic or resolved at runtime.
5. Repository exploration protocol
Before implementing a feature:
Read the applicable agent instructions.
Consult the relevant architecture map and codemap.
Search for the existing implementation, related symbols, callers, and tests.
Inspect the smallest set of files sufficient to understand the change.
Reuse established interfaces, abstractions, and conventions.
Expand the search only when the initial evidence is insufficient or contradictory.
Avoid repeatedly rediscovering documented facts. Verify documentation against source code whenever there is reason to suspect it is stale.
6. New modules and architectural changes
Whenever a new subsystem, module, public interface, or significant execution path is introduced:
Document its responsibility and boundaries.
Record its key entry points and dependencies.
Identify the intended extension points.
Link relevant tests and examples.
Record significant design decisions and constraints.
Update generated indexes and graphs.
Keep documentation concise and focused on helping a future contributor implement the next feature.
7. Validation and completion criteria
A task that changes architecture or repository navigation is not complete until the affected maps are updated and validated.
Where automation exists, verify that:
Documented file paths resolve.
Referenced symbols exist.
Generated artifacts match the current source.
Documentation links resolve.
Required generation and validation commands succeed.
Do not claim that maps have been regenerated or validated unless the corresponding commands have actually been executed.
If a map cannot be updated reliably, report what is stale, why it could not be updated, and what remains to be done.
Do not modify source code merely to make documentation appear consistent with an incorrect description. Treat the implementation as authoritative unless the task explicitly changes the architecture.
