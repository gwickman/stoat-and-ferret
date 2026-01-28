# Validation Patterns for pydantic-settings v2

Custom validators and field types for settings validation.

## Validator Types

pydantic-settings uses the same validation system as pydantic v2:

| Type | When It Runs | Use Case |
|------|--------------|----------|
| `BeforeValidator` | Before type coercion | Transform raw input |
| `AfterValidator` | After type coercion | Validate parsed value |
| `WrapValidator` | Wraps pydantic's validation | Error handling, fallbacks |
| `PlainValidator` | Replaces pydantic's validation | Complete custom logic |

## Recommended Pattern: Annotated Types

Use `Annotated` with validators for reusable validated types:

```python
from typing import Annotated
from pathlib import Path
from pydantic import AfterValidator, Field

def validate_positive(value: int) -> int:
    if value <= 0:
        raise ValueError(f'Must be positive, got {value}')
    return value

def validate_directory_exists(path: Path) -> Path:
    if not path.is_dir():
        raise ValueError(f'Directory does not exist: {path}')
    return path

def validate_file_exists(path: Path) -> Path:
    if not path.is_file():
        raise ValueError(f'File does not exist: {path}')
    return path

# Reusable validated types
PositiveInt = Annotated[int, AfterValidator(validate_positive)]
ExistingDir = Annotated[Path, AfterValidator(validate_directory_exists)]
ExistingFile = Annotated[Path, AfterValidator(validate_file_exists)]
```

## Field-Level Constraints

Use `Field()` for simple constraints (preferred over custom validators):

```python
from pydantic import Field

class Settings(BaseSettings):
    # Numeric constraints
    api_port: int = Field(default=8000, ge=1, le=65535)
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout_seconds: float = Field(default=30.0, gt=0)

    # String constraints
    api_key: str = Field(min_length=32, max_length=64)
    log_level: str = Field(default='INFO', pattern=r'^(DEBUG|INFO|WARNING|ERROR)$')
```

## Decorator Syntax (@field_validator)

For complex validation logic or cross-field dependencies:

```python
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    read_replica_url: str | None = None

    @field_validator('database_url', mode='after')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(('sqlite://', 'postgresql://')):
            raise ValueError('Database URL must be sqlite:// or postgresql://')
        return v

    @model_validator(mode='after')
    def validate_replica_different(self) -> 'Settings':
        if self.read_replica_url and self.read_replica_url == self.database_url:
            raise ValueError('Read replica must be different from primary')
        return self
```

## BeforeValidator: Transform Raw Input

Use for normalizing input before type conversion:

```python
from typing import Annotated, Any
from pydantic import BeforeValidator

def normalize_path(value: Any) -> Any:
    """Expand ~ and environment variables in paths."""
    if isinstance(value, str):
        import os
        return os.path.expanduser(os.path.expandvars(value))
    return value

ExpandedPath = Annotated[Path, BeforeValidator(normalize_path)]

class Settings(BaseSettings):
    data_dir: ExpandedPath = Field(default=Path('~/.stoat-ferret/data'))
```

## Environment Variable Specific Validation

pydantic-settings validates after environment variable parsing:

```python
from typing import Annotated
from pydantic import BeforeValidator

def parse_list(value: Any) -> Any:
    """Parse comma-separated string to list."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return value

StringList = Annotated[list[str], BeforeValidator(parse_list)]

class Settings(BaseSettings):
    allowed_origins: StringList = Field(default_factory=list)

# Environment: STOAT_ALLOWED_ORIGINS="http://localhost:3000, http://localhost:8000"
# Result: ['http://localhost:3000', 'http://localhost:8000']
```

## Validation for stoat-and-ferret

Recommended validators for v003:

```python
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_port(port: int) -> int:
    """Ensure port is in valid range."""
    if not 1 <= port <= 65535:
        raise ValueError(f'Port must be 1-65535, got {port}')
    return port


def validate_parent_exists(path: Path) -> Path:
    """Validate parent directory exists for file creation."""
    if not path.parent.exists():
        raise ValueError(f'Parent directory does not exist: {path.parent}')
    return path


def expand_path(value: Any) -> Any:
    """Expand environment variables and ~ in paths."""
    if isinstance(value, str):
        import os
        return os.path.expanduser(os.path.expandvars(value))
    return value


# Type aliases for settings
Port = Annotated[int, AfterValidator(validate_port)]
WritablePath = Annotated[Path, BeforeValidator(expand_path), AfterValidator(validate_parent_exists)]
ExpandedPath = Annotated[Path, BeforeValidator(expand_path)]
```

## Key Recommendations

1. **Prefer Field constraints** for simple numeric/string validation (ge, le, min_length, pattern)

2. **Use Annotated types** for reusable validation patterns

3. **Validate at appropriate time**:
   - `BeforeValidator`: Input transformation (expand paths, parse lists)
   - `AfterValidator`: Business logic validation (port range, path exists)

4. **Don't over-validate**: Only validate what actually matters for the application

5. **Provide clear error messages**: Include the actual value in error messages
