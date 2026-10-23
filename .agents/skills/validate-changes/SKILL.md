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