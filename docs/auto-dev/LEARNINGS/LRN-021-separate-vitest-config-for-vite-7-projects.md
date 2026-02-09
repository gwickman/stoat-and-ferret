## Context

When using Vite 7 with Vitest 4, the inline `test` configuration block inside `vite.config.ts` causes TypeScript errors. This is a breaking change from earlier Vite/Vitest versions where inline test config worked.

## Learning

Use a separate `vitest.config.ts` file instead of inline test configuration in `vite.config.ts` when using Vite 7+ with Vitest 4+. This provides clean separation of build and test configuration and avoids TypeScript compatibility issues.

## Evidence

- v005 Theme 01 (frontend-scaffolding): Discovered TypeScript error when attempting inline `test` config in `vite.config.ts` with Vite 7 + Vitest 4
- Separate `vitest.config.ts` file resolved the issue cleanly
- Also needed `exclude: ['e2e/**']` in vitest config to prevent picking up Playwright tests (Theme 04)

## Application

- Any React/TypeScript project using Vite 7+ with Vitest 4+
- When upgrading from older Vite/Vitest versions where inline config worked
- Remember to add E2E test directory exclusions in vitest config when adding Playwright