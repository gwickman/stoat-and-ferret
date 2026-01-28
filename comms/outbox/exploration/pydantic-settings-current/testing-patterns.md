# Testing Patterns for pydantic-settings v2

How to override settings in tests for stoat-and-ferret.

## Overview

Two main approaches for testing with pydantic-settings:

1. **Environment variable manipulation** (pytest monkeypatch)
2. **Direct instantiation** with overrides

## Pattern 1: Environment Variables with monkeypatch

Best for integration tests that need realistic settings loading:

```python
import pytest
from stoat_ferret.config import Settings


def test_settings_from_environment(monkeypatch):
    """Test settings loaded from environment variables."""
    monkeypatch.setenv('STOAT_DATABASE_PATH', '/tmp/test.db')
    monkeypatch.setenv('STOAT_API_PORT', '9000')
    monkeypatch.setenv('STOAT_DEBUG', 'true')

    settings = Settings()

    assert str(settings.database_path) == '/tmp/test.db'
    assert settings.api_port == 9000
    assert settings.debug is True


def test_settings_default_values(monkeypatch):
    """Test default values when no env vars set."""
    # Clear any existing STOAT_ variables
    for key in list(monkeypatch._env_items.keys()):
        if key.startswith('STOAT_'):
            monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.api_port == 8000
    assert settings.debug is False
```

## Pattern 2: Direct Instantiation

Best for unit tests with specific values:

```python
from pathlib import Path
from stoat_ferret.config import Settings


def test_settings_direct_override():
    """Test settings with direct constructor values."""
    settings = Settings(
        database_path=Path('/tmp/test.db'),
        api_port=9000,
        debug=True,
        _env_file=None,  # Disable .env loading
    )

    assert settings.database_path == Path('/tmp/test.db')
    assert settings.api_port == 9000


def test_validation_rejects_invalid_port():
    """Test port validation."""
    with pytest.raises(ValueError, match='Port must be 1-65535'):
        Settings(api_port=70000)
```

## Pattern 3: Fixture for Test Settings

Create a reusable test settings fixture:

```python
import pytest
from pathlib import Path
from stoat_ferret.config import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Provide test settings with isolated database."""
    return Settings(
        database_path=tmp_path / 'test.db',
        temp_dir=tmp_path / 'temp',
        debug=True,
        _env_file=None,
    )


def test_with_fixture(test_settings: Settings):
    """Test using the settings fixture."""
    assert test_settings.debug is True
    assert 'test.db' in str(test_settings.database_path)
```

## Pattern 4: Override FastAPI Dependencies

For FastAPI integration tests:

```python
import pytest
from fastapi.testclient import TestClient
from stoat_ferret.main import app, get_settings
from stoat_ferret.config import Settings


def get_test_settings() -> Settings:
    """Return test settings."""
    return Settings(
        database_path=Path(':memory:'),
        debug=True,
        _env_file=None,
    )


@pytest.fixture
def client():
    """Test client with overridden settings."""
    app.dependency_overrides[get_settings] = get_test_settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_endpoint_with_test_settings(client):
    """Test endpoint uses test settings."""
    response = client.get('/status')
    assert response.status_code == 200
```

## Pattern 5: Mock .env File

Test .env file loading:

```python
def test_dotenv_loading(tmp_path: Path):
    """Test loading settings from .env file."""
    env_file = tmp_path / '.env'
    env_file.write_text(
        'STOAT_DATABASE_PATH=/custom/path.db\n'
        'STOAT_API_PORT=9999\n'
    )

    settings = Settings(_env_file=str(env_file))

    assert str(settings.database_path) == '/custom/path.db'
    assert settings.api_port == 9999
```

## Pattern 6: Disable .env Loading

Prevent .env interference in tests:

```python
class TestSettings(Settings):
    """Settings subclass that ignores .env files."""

    model_config = SettingsConfigDict(
        env_prefix='STOAT_',
        env_file=None,  # Disable .env
    )


def test_without_dotenv_interference():
    """Test with no .env loading."""
    settings = TestSettings(api_port=8080)
    assert settings.api_port == 8080
```

## Recommended conftest.py

```python
# tests/conftest.py
import pytest
from pathlib import Path
from stoat_ferret.config import Settings


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch) -> Settings:
    """
    Provide fully isolated test settings.

    - Uses tmp_path for file paths
    - Clears STOAT_ environment variables
    - Disables .env loading
    """
    # Clear any existing STOAT_ variables
    import os
    for key in list(os.environ.keys()):
        if key.startswith('STOAT_'):
            monkeypatch.delenv(key)

    return Settings(
        database_path=tmp_path / 'test.db',
        temp_dir=tmp_path / 'temp',
        debug=True,
        _env_file=None,
    )


@pytest.fixture
def monkeypatch_settings(monkeypatch):
    """
    Return a helper to set STOAT_ environment variables.

    Usage:
        def test_foo(monkeypatch_settings):
            monkeypatch_settings(api_port=9000, debug=True)
            settings = Settings()
    """
    def setter(**kwargs):
        for key, value in kwargs.items():
            env_key = f'STOAT_{key.upper()}'
            monkeypatch.setenv(env_key, str(value))
    return setter
```

## Key Recommendations

1. **Use `_env_file=None`** to disable .env loading in tests

2. **Use tmp_path** for file/database paths to ensure test isolation

3. **Clear environment variables** to prevent test pollution

4. **Use fixtures** for common test settings configurations

5. **Override FastAPI dependencies** for endpoint testing instead of mocking settings directly

6. **Test validation errors** with `pytest.raises` to ensure constraints work
