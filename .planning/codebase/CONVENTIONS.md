# Coding Conventions

**Analysis Date:** 2026-04-24

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `api_client.py`, `formatting.py`, `validation.py`
- Package directories use lowercase with underscores: `intervals_mcp_server`, `src/intervals_mcp_server/tools`
- Test files follow pytest convention: `test_*.py` (e.g., `test_formatting.py`, `test_server.py`)

**Functions:**
- Public functions use lowercase with underscores: `get_config()`, `format_activity_summary()`, `resolve_athlete_id()`
- Private/internal functions are prefixed with underscore: `_get_httpx_client()`, `_parse_activities_from_result()`, `_format_training_metrics()`
- Async functions use same naming convention as sync: `async def make_intervals_request()`, `async def get_wellness_data()`
- Tool functions (MCP endpoints) use present tense verbs: `get_activities`, `get_event_by_id`, `add_or_update_event`, `delete_event`

**Variables:**
- Local variables and parameters use lowercase with underscores: `api_key`, `athlete_id`, `start_date`, `error_message`
- Constants use UPPERCASE with underscores: typically environment variables like `API_KEY`, `ATHLETE_ID`
- Single letter variables reserved for loop counters: `for i, interval in enumerate(...)`

**Types:**
- Class names use PascalCase: `Config`, `Value`, `Step`, `WorkoutDoc`, `SportSettings`
- Type hints use modern Python 3.12+ syntax: `dict[str, Any]`, `list[dict[str, Any]]`, `str | None` (union types)
- Enum members use UPPERCASE with underscores: `PERCENT_FTP`, `POWER_ZONE`, `HR_ZONE`
- Enum classes use PascalCase: `ValueUnits`, `WorkoutTarget`, `HrTarget`, `Intensity`

## Code Style

**Formatting:**
- Tool: Ruff (both linter and formatter)
- Line length: 100 characters
- Configuration file: `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`

**Linting:**
- Tool: Ruff
- Key rules enabled:
  - E (pycodestyle errors)
  - W (pycodestyle warnings)
  - F (pyflakes)
  - C (flake8-comprehensions)
  - B (flake8-bugbear)
- Key rules disabled:
  - E501 (line too long, handled by formatter)
  - B008 (function calls in argument defaults)
  - C901 (complexity)
  - G004 (f-string in logging)
- Max complexity: 10 (McCabe)
- Max function arguments: 8
- Unused variable pattern: Variables with underscore prefix or surrounded by underscores are allowed

## Import Organization

**Order:**
1. Standard library imports: `import logging`, `from typing import Any`, `from dataclasses import dataclass`
2. Third-party imports: `import httpx`, `from mcp.server.fastmcp import FastMCP`
3. Local imports: `from intervals_mcp_server.api.client import make_intervals_request`

**Path Aliases:**
- Full imports from package root are used: `from intervals_mcp_server.config import get_config`
- No import aliases observed (e.g., no `import something as s`)
- Conditional imports with error handling for optional dependencies: See `config.py` for python-dotenv example

**Pylint Directives:**
- Inline comments used sparingly: `# pylint: disable=wrong-import-position` when imports must follow module setup
- `# noqa: F401` used for intentional re-exports or required imports that appear unused (e.g., `from intervals_mcp_server.mcp_instance import mcp  # noqa: F401`)
- Global statement comments in singleton pattern: `# pylint: disable=global-statement  # noqa: PLW0603`

## Error Handling

**Patterns:**
- API errors return error dict with structure: `{"error": True, "status_code": ..., "message": "..."}`
- User-facing error messages are constructive and include guidance (e.g., "Please check your API key")
- Exceptions are caught by type and logged with context: `except httpx.HTTPStatusError as e:`, `except JSONDecodeError:`
- Validation functions raise `ValueError` with descriptive messages for invalid input
- Tool functions return error messages as strings (for MCP protocol compatibility): `return f"Error: {result.get('message')}"`

**Error Recovery:**
- HTTP client closure is handled with lazy recreation: See `_get_httpx_client()` which recreates closed client
- Retry logic on client closure: Attempts request once more after client recreation

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
- Logger created per module: `logger = logging.getLogger("intervals_icu_mcp_server")`
- Logging configured in main entry point: `logging.basicConfig()` in `server.py`
- Log levels used appropriately:
  - `logger.debug()` for request bodies and internal details
  - `logger.info()` for configuration loaded
  - `logger.warning()` for client recreation/recovery scenarios
  - `logger.error()` for API errors and exceptions
- Log messages include context: `logger.error("HTTP error: %s - %s", error_code, error_text)`

## Comments

**When to Comment:**
- Comments explain *why*, not *what* (code is self-documenting)
- Special cases and workarounds: See `client.py` comments on client closure handling
- Complex type conversions or API quirks documented inline
- Comments used sparingly; clear naming preferred over comments

**JSDoc/TSDoc:**
- Module docstrings: All modules have docstring describing purpose and contents
  - Format: Triple-quoted string at top of file before imports
  - Includes brief description and usage notes for main modules
- Function docstrings: All public and complex functions documented
  - Format: Google-style docstrings (Args, Returns, Raises sections)
  - Example from `format_wellness_entry()`:
    ```python
    """Format wellness entry data into a readable string.

    Formats various wellness metrics including training metrics, vital signs,
    sleep data, menstrual tracking, subjective feelings, nutrition, and activity.

    Args:
        entries: Dictionary containing wellness data fields...
        include_all_fields: If True, any fields not covered...

    Returns:
        A formatted string representation of the wellness entry.
    """
    ```

## Function Design

**Size:** Functions kept small and focused
- Private helper functions extract common logic: `_format_training_metrics()`, `_parse_response()`
- Complex tools use multiple private functions to organize logic: `get_activities()` uses 4 helpers
- Complexity disabled in linting for unavoidable cases: `# pylint: disable=too-many-arguments`

**Parameters:**
- Type hints required: `def get_wellness_data(athlete_id: str | None = None, ...)`
- Default parameters for optional values: `include_all_fields: bool = False`
- Union types used for parameters: `str | None` preferred over `Optional[str]`

**Return Values:**
- Functions return tuples for multiple values: `tuple[str, str | None]` from `resolve_athlete_id()`
- Consistent return types across function variants (e.g., all formatting functions return strings)
- Tool functions (MCP endpoints) always return strings (protocol requirement)

## Module Design

**Exports:**
- Modules organized by functionality: `tools/activities.py`, `utils/formatting.py`, `api/client.py`
- Public functions documented with docstrings; private functions prefixed with underscore
- `__all__` variable defined in type definition modules: `types.py` has `__all__` listing exports

**Barrel Files:**
- `__init__.py` files in packages may re-export for convenience
- Example: `tools/__init__.py` may import from submodules
- Avoid circular imports by importing shared components from specific module: `from intervals_mcp_server.mcp_instance import mcp`

**Dataclass Usage:**
- Used extensively for structured data: `Config`, `Value`, `Step`, `WorkoutDoc`, `SportSettings`
- All dataclass instances support `to_dict()`, `from_dict()`, `to_json()`, `from_json()` methods
- Optional fields use `Optional[Type]`: `description: Optional[str] = None`
- Dataclass fields with many options marked with pylint disable: `class Step:  # pylint: disable=too-many-instance-attributes`

## API Client Patterns

**Request Handling:**
- All API requests go through single function: `make_intervals_request()`
- Located in `src/intervals_mcp_server/api/client.py`
- Handles authentication, headers, error responses uniformly
- Returns parsed JSON on success, error dict on failure

**Configuration:**
- Configuration loaded once via singleton pattern: `get_config()` in `config.py`
- Environment variables parsed with defaults: `os.getenv("API_KEY", "")`
- Validation performed at load time: `validate_athlete_id()` called during config init

---

*Convention analysis: 2026-04-24*
