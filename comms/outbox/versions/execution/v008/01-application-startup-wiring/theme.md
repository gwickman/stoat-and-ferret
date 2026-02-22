# Theme 01: application-startup-wiring

## Description

Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence, so a fresh application start produces a fully functional system without manual intervention. All three features share the same modification point (`src/stoat_ferret/api/app.py` lifespan) and represent the same class of work: connecting infrastructure built in v002/v003 that was never wired.

## Features

- **001-database-startup**
- **002-logging-startup**
- **003-orphaned-settings**

## Live Progress

For current per-feature execution status, see `version-state.json` in the version outbox directory.
