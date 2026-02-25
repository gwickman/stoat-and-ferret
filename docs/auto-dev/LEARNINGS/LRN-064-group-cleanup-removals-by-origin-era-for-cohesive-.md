## Context

When a cleanup effort targets multiple items introduced across different project phases (e.g., deprecated APIs from v1 and v2, legacy modules from different feature cycles), the removal order matters for reviewability and risk management.

## Learning

Group items by their origin era or introduction phase, then remove them in chronological order from oldest to newest. This creates naturally cohesive PRs where all removed items share the same historical context, making reviews easier and building confidence progressively — simple, well-understood old code first, then more recent and potentially complex code.

## Evidence

A binding cleanup theme organized three features by era: a dead Python bridge function first (simplest, pure Python), then v001-era bindings (5 items with shared range/sanitize context), then v006-era bindings (6 items with shared expression/filter context). Each PR was self-contained and reviewable because all items shared origin context. The progression from simple to complex built reviewer confidence across the series.

## Application

1. When planning multi-item cleanup, inventory all items and tag them by origin (phase, version, feature)
2. Sort groups chronologically — oldest first
3. Create one PR per group, keeping all items from the same origin together
4. Start with the simplest group to establish the removal pattern
5. Each subsequent PR can reference the established pattern from earlier PRs