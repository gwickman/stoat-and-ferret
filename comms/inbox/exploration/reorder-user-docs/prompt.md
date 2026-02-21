
# Reorganise User Documentation with Numeric Ordering

## Objective
Rename all files in `docs/manual/` and `docs/setup/` so they have numeric prefixes indicating the recommended reading order. Use zero-padded two-digit prefixes with underscores (e.g., `00_README.md`, `01_prerequisites.md`).

## Current Files

### docs/setup/
- README.md
- prerequisites.md
- development-setup.md
- docker-setup.md
- configuration.md
- troubleshooting.md

### docs/manual/
- README.md
- getting-started.md
- api-overview.md
- api-reference.md
- effects-guide.md
- timeline-guide.md
- gui-guide.md
- rendering-guide.md
- ai-integration.md
- glossary.md

## Required Reading Order

### docs/setup/ — rename to:
1. `00_README.md` (was README.md)
2. `01_prerequisites.md` (was prerequisites.md)
3. `02_development-setup.md` (was development-setup.md)
4. `03_docker-setup.md` (was docker-setup.md)
5. `04_configuration.md` (was configuration.md)
6. `05_troubleshooting.md` (was troubleshooting.md)

### docs/manual/ — rename to:
1. `00_README.md` (was README.md)
2. `01_getting-started.md` (was getting-started.md)
3. `02_api-overview.md` (was api-overview.md)
4. `03_api-reference.md` (was api-reference.md)
5. `04_effects-guide.md` (was effects-guide.md)
6. `05_timeline-guide.md` (was timeline-guide.md)
7. `06_gui-guide.md` (was gui-guide.md)
8. `07_rendering-guide.md` (was rendering-guide.md)
9. `08_ai-integration.md` (was ai-integration.md)
10. `09_glossary.md` (was glossary.md)

## Additional Requirements

After renaming, update ALL internal cross-references within every file. Any markdown links that reference the old filenames (e.g., `[Prerequisites](prerequisites.md)`) must be updated to use the new prefixed filenames (e.g., `[Prerequisites](01_prerequisites.md)`). Also update any cross-references between the two folders (e.g., `../setup/development-setup.md` becomes `../setup/02_development-setup.md`).

Use `git mv` for the renames so git tracks the file history properly.

## Output Requirements

Write a `README.md` to `comms/outbox/exploration/reorder-user-docs/` listing:
- Every rename performed (old → new)
- Every cross-reference updated (file, old link → new link)

## Commit Instructions
When complete, stage and commit all changes with message: "docs: add numeric ordering prefixes to manual and setup documentation"
Include all renamed files under `docs/manual/` and `docs/setup/`.
