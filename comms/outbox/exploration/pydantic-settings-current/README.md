# pydantic-settings v2 Current Patterns

Research findings for stoat-and-ferret v003 externalized configuration.

## Summary

pydantic-settings v2 (current: 2.9.1) provides type-safe configuration management that integrates naturally with FastAPI. Key changes from v1:

- `BaseSettings` moved to `pydantic_settings` package (separate from pydantic)
- `model_config = SettingsConfigDict(...)` replaces `class Config:`
- Default values are validated by default
- Enhanced nested model support with `env_nested_delimiter`

## Recommended Patterns for stoat-and-ferret

### 1. Settings Class Structure

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='STOAT_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

    database_path: str = Field(default='data/stoat.db')
    api_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
```

### 2. Environment Variable Mapping

With `env_prefix='STOAT_'`:
- `database_path` reads from `STOAT_DATABASE_PATH`
- `api_port` reads from `STOAT_API_PORT`
- `debug` reads from `STOAT_DEBUG`

### 3. FastAPI Integration

Use cached singleton pattern:

```python
from functools import lru_cache
from fastapi import Depends

@lru_cache
def get_settings() -> Settings:
    return Settings()

@app.get('/status')
async def status(settings: Settings = Depends(get_settings)):
    return {'port': settings.api_port}
```

### 4. Test Override Pattern

```python
def test_with_custom_settings(monkeypatch):
    monkeypatch.setenv('STOAT_DATABASE_PATH', ':memory:')
    settings = Settings()
    assert settings.database_path == ':memory:'
```

## Source Priority (Highest to Lowest)

1. Constructor arguments
2. Environment variables
3. `.env` file values
4. Field defaults

## Files in This Exploration

| File | Contents |
|------|----------|
| [settings-class.md](./settings-class.md) | Concrete Settings class for stoat-and-ferret |
| [validation-patterns.md](./validation-patterns.md) | Custom validators and field constraints |
| [testing-patterns.md](./testing-patterns.md) | How to override settings in tests |
| [fastapi-integration.md](./fastapi-integration.md) | Dependency injection patterns |

## References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [DeepWiki: pydantic-settings](https://deepwiki.com/pydantic/pydantic-settings)
