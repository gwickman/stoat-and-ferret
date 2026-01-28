# Implementation Plan: Clip Repository

## Step 1: Create Repository
Create `src/stoat_ferret/db/clip_repository.py` with AsyncClipRepository protocol, AsyncSQLiteClipRepository, and AsyncInMemoryClipRepository.

## Step 2: Add Contract Tests
Create `tests/test_clip_repository_contract.py` with parametrized fixtures testing both implementations.

## Verification
- All CRUD operations work
- list_by_project returns ordered clips
- Contract tests pass for both implementations