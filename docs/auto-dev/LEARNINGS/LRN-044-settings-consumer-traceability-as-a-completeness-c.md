## Context

Configuration settings classes (e.g., Pydantic `Settings`) can accumulate fields that are defined but never consumed by production code. These orphaned settings create confusion about whether they're intentionally unused or were simply forgotten during wiring.

## Learning

After any settings wiring work, verify that every settings field has at least one production consumer. This "settings traceability" check catches configuration drift where fields exist in the schema but aren't consumed. It can be done manually (grep for field names) or automated as a lint rule that maps each Settings field to its usage sites.

## Evidence

v008 feature 003 (orphaned settings) found that 2 of 9 `Settings` fields (`debug`, `ws_heartbeat_interval`) were defined but unconsumed by production code. After wiring them, all 9 fields had production consumers. The retrospective recommended automating this as a lint check to prevent future orphaned settings.

## Application

After adding or modifying settings fields:
1. Verify each field has at least one production code consumer (not just test usage)
2. Consider adding an automated check that maps Settings fields to import sites
3. Treat orphaned settings as low-priority tech debt — they indicate incomplete wiring that may cause operator confusion