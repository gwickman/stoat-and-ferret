# Externalized Settings

## Goal
Implement pydantic-settings for configuration with environment variable support.

## Requirements

### FR-001: Settings Class
Create `src/stoat_ferret/api/settings.py` with Settings class:
- `database_path`: str = "data/stoat.db"
- `api_host`: str = "127.0.0.1"
- `api_port`: int = 8000
- `debug`: bool = False
- `log_level`: str = "INFO"

### FR-002: Environment Prefix
All settings read from `STOAT_` prefixed environment variables:
- `STOAT_DATABASE_PATH`
- `STOAT_API_PORT`
- etc.

### FR-003: .env File Support
Load from `.env` file if present.

### FR-004: Singleton Pattern
Use `@lru_cache` for `get_settings()` function.

### FR-005: Validation
- `api_port` must be 1-65535
- `log_level` must be valid Python log level

### FR-006: Dependencies
Add to pyproject.toml:
- `pydantic-settings>=2.0`

## Acceptance Criteria
- [ ] Settings class defined with all fields
- [ ] Environment variables override defaults
- [ ] `.env` file loaded if present
- [ ] `get_settings()` returns cached instance
- [ ] Invalid values raise validation error