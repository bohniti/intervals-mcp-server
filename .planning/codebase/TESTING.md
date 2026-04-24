# Testing Patterns

**Analysis Date:** 2026-04-24

## Test Framework

**Runner:**
- pytest 8.3.5+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- Python test files detected: `test_*.py` pattern

**Assertion Library:**
- Standard `assert` statements (Python built-in)
- Pytest assertions with direct comparisons: `assert "Activity: Morning Ride" in result`
- No external assertion library; pytest's assertion introspection used

**Run Commands:**
```bash
pytest -q                    # Run all tests (quiet mode, from pyproject.toml default)
pytest -v tests              # Verbose test run (used in pre-commit hook)
pytest tests/test_formatting.py  # Run specific test file
pytest tests/test_server.py::test_get_activities  # Run specific test
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- Separate from source code (`src/` directory)
- Pattern: `tests/test_*.py` for unit tests

**Naming:**
- Test files: `test_*.py` (e.g., `test_formatting.py`, `test_server.py`, `test_value.py`)
- Test functions: `test_*` (e.g., `test_format_activity_summary`, `test_get_activities`)
- Test classes: Not used; flat function structure

**Structure:**
```
tests/
├── __init__.py
├── test_formatting.py       # Tests for utils.formatting module
├── test_server.py           # Tests for server/tools functionality
├── test_value.py            # Tests for utils.types.Value
├── test_make_intervals_request.py  # Tests for API client error handling
├── sample_data.py           # Shared test fixtures/sample data
└── ressources/              # Test data files
    ├── wellness_entry.json
    └── wellness_entry_formatted.txt
```

## Test Structure

**Suite Organization:**
```python
"""
Unit tests for formatting utilities in intervals_mcp_server.utils.formatting.

These tests verify that the formatting functions produce expected output strings for activities, workouts, wellness entries, events, and intervals.
"""

import json
from intervals_mcp_server.utils.formatting import (
    format_activity_summary,
    format_workout,
)
from tests.sample_data import INTERVALS_DATA


def test_format_activity_summary():
    """
    Test that format_activity_summary returns a string containing the activity name and ID.
    """
    data = {
        "name": "Morning Ride",
        "id": 1,
        "type": "Ride",
    }
    result = format_activity_summary(data)
    assert "Activity: Morning Ride" in result
    assert "ID: 1" in result
```

**Patterns:**
- One test file per module being tested
- Docstrings on all test functions describing what is tested
- Setup via function parameters (monkeypatch, caplog) rather than setUp/tearDown
- Test data included inline or imported from `sample_data.py`
- Clear arrange-act-assert structure

## Mocking

**Framework:** pytest's built-in `monkeypatch` fixture

**Patterns:**
```python
def test_get_activities(monkeypatch):
    """Test that mocks API requests."""
    sample = {
        "name": "Morning Ride",
        "id": 123,
    }

    async def fake_request(*_args, **_kwargs):
        return [sample]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activities(athlete_id="1", limit=1, include_unnamed=True))
    assert "Morning Ride" in result
```

**Mock Classes:**
- Custom mock classes created for complex scenarios: `MockBadJSONResponse` in `test_make_intervals_request.py`
- Mock classes replicate interface of real objects: `is_closed` attribute, `async` methods, etc.
- Monkeypatch used to inject mocks: `monkeypatch.setattr(..., MockAsyncClient())`

**What to Mock:**
- External API calls: `make_intervals_request()`
- HTTP client: `httpx.AsyncClient` when testing client behavior
- Environment configuration: Config singleton for environment-dependent tests
- Module-level singletons: `_config_instance` reset between tests

**What NOT to Mock:**
- Formatting functions (pure functions with predictable output)
- Validation functions (simple string/type checks)
- Type definitions and dataclasses
- Actual assertion logic in tests

## Fixtures and Factories

**Test Data:**
```python
# From tests/sample_data.py
INTERVALS_DATA = {
    "id": "activity_123",
    "analyzed": True,
    "icu_intervals": [
        {
            "label": "Rep 1",
            "type": "interval",
            "elapsed_time": 300,
            "average_watts": 350,
            # ... more fields
        }
    ],
    "icu_groups": []
}

# Used in tests
def test_format_intervals():
    result = format_intervals(INTERVALS_DATA)
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result
```

**Location:**
- Shared fixtures in `tests/sample_data.py`
- Inline data for simple tests
- Resource files in `tests/ressources/` for complex data (JSON, text files)

**Patterns:**
- Simple dict factories inline in test functions
- Complex fixtures in `sample_data.py` module
- Resource files loaded with explicit encoding: `open("tests/ressources/wellness_entry.json", "r", encoding="utf-8")`

## Coverage

**Requirements:** Not enforced

**View Coverage:**
```bash
pytest --cov=src/intervals_mcp_server --cov-report=html
```

No coverage threshold configured, but `--cov` flag can be used manually.

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes
- Approach: Mock external dependencies (API, config)
- Examples: `test_format_activity_summary()`, `test_str_percent_ftp()`
- Location: All tests in `tests/` directory follow unit test pattern

**Integration Tests:**
- Scope: Not separated; some tests in `test_server.py` test tool functions with mocked API
- Approach: Mock API responses but test full tool flow: `test_get_activities()` tests async function with mocked request

**E2E Tests:**
- Not used in this codebase

## Common Patterns

**Async Testing:**
```python
import asyncio

async def fake_request(*_args, **_kwargs):
    return [sample]

# Run async function in sync test
result = asyncio.run(get_activities(athlete_id="1", limit=1))
```

**Error Testing:**
```python
def test_make_intervals_request_bad_json(monkeypatch, caplog):
    """Test error handling for invalid JSON responses."""
    monkeypatch.setattr(server, "httpx_client", MockAsyncClient())

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(server.make_intervals_request("/bad"))

    assert result["error"] is True
    assert "Invalid JSON in response" in result["message"]
```

**Configuration Mocking:**
```python
def test_with_custom_config(monkeypatch):
    """Test with mocked environment and config."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("ATHLETE_ID", "i123")
    # Reset singleton so config reloads from env
    monkeypatch.setattr("intervals_mcp_server.config._config_instance", None)
```

**Logging Capture:**
```python
def test_with_logging(monkeypatch, caplog):
    """Test that logs error messages."""
    with caplog.at_level(logging.ERROR):
        result = asyncio.run(function_that_logs())
    
    assert "error message" in caplog.text
```

**Resource File Testing:**
```python
def test_format_wellness_entry():
    """Test formatting against resource file."""
    with open("tests/ressources/wellness_entry.json", "r", encoding="utf-8") as f:
        entry = json.load(f)
    result = format_wellness_entry(entry)

    with open("tests/ressources/wellness_entry_formatted.txt", "r", encoding="utf-8") as f:
        expected_result = f.read()
    assert result == expected_result
```

## Test Environment

**Async Loop:**
- Config: `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml`
- Package: `pytest-asyncio>=0.21` required for async test support
- Scope: New loop per test function (isolation)

**Path Setup:**
- Some tests add project root to sys.path: `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))`
- Allows running tests without installing package
- Pattern used in `test_server.py`, `test_make_intervals_request.py`

**Environment Variables:**
- Set defaults before import in test files: `os.environ.setdefault("API_KEY", "test")`
- Monkeypatch used for per-test overrides: `monkeypatch.setenv("API_KEY", "test_value")`

## Pre-Commit Testing

**Hook Configuration:** `.pre-commit-config.yaml`
```yaml
- repo: local
  hooks:
    - id: tests
      name: run tests
      entry: pytest -v tests
      language: system
      pass_filenames: false
      always_run: true
      stages: [pre-push]
```

- Tests run on `pre-push` stage (not pre-commit)
- All tests run regardless of changed files (`always_run: true`)
- Verbose output (`-v`) used
- Tests must pass before push

---

*Testing analysis: 2026-04-24*
