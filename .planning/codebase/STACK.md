# Technology Stack

**Analysis Date:** 2026-04-24

## Languages

**Primary:**
- Python 3.12+ - All server code, CLI tools, tests

## Runtime

**Environment:**
- Python 3.12 (minimum requirement in `pyproject.toml`)
- CPython runtime

**Package Manager:**
- uv (recommended, modern Python package manager)
- pip (fallback support)
- Lockfile: `uv.lock` present and tracked

## Frameworks

**Core:**
- Model Context Protocol (MCP) 1.22.0 - MCP server framework via `mcp.server.fastmcp.FastMCP`
  - CLI component via `mcp[cli]` extra for running tools

**HTTP Client:**
- httpx 0.28.1 - Async HTTP client for API requests in `src/intervals_mcp_server/api/client.py`

**Environment Configuration:**
- python-dotenv 1.0.0+ - Load environment variables from `.env` files in `src/intervals_mcp_server/config.py`

**Testing:**
- pytest 8.3.5+ - Test runner configured in `pyproject.toml`
- pytest-asyncio 0.21+ - Async test support
- pytest-mock 3.12.0 - Mocking support in tests

**Development/Linting:**
- ruff 0.1.0+ - Code linting and formatting (configured in `pyproject.toml`)
- mypy 1.0.0+ - Static type checking
- pre-commit - Git hooks framework (configuration in `.pre-commit-config.yaml`)
- hatch - Build system (via hatchling build backend)

## Key Dependencies

**Critical:**
- mcp>=1.4.0 - Model Context Protocol SDK - Core framework for exposing tools to Claude
- httpx>=0.25.0 - Async HTTP communication with Intervals.icu API
- python-dotenv>=1.0.0 - Environment variable management for API credentials

**Build:**
- hatchling - Build backend for packaging (specified in `[build-system]`)

## Configuration

**Environment:**
- Loaded from `.env` file via python-dotenv in `src/intervals_mcp_server/config.py`
- Configuration dataclass in `src/intervals_mcp_server/config.py`: `Config` with fields:
  - `API_KEY` (required) - Intervals.icu API authentication
  - `ATHLETE_ID` (required) - Athlete identifier
  - `INTERVALS_API_BASE_URL` (optional, defaults to `https://intervals.icu/api/v1`)
  - `user_agent` (auto-set to `intervalsicu-mcp-server/1.0`)

**Build:**
- `pyproject.toml` - Project metadata, dependencies, tool configuration
- Build configuration in `[tool.hatch.build]` section
- Package location: `src/intervals_mcp_server`

**Code Quality Tools:**
- Ruff config: `[tool.ruff]` in `pyproject.toml` - line length 100, Python 3.11+
- Pylint config: `[tool.pylint.design]` in `pyproject.toml` - max args 8
- Pytest config: `[tool.pytest.ini_options]` in `pyproject.toml` - testpaths: `tests/`
- Pre-commit hooks: `.pre-commit-config.yaml` - ruff, typos, pytest, no-commit-to-branch

## Platform Requirements

**Development:**
- Python 3.12 or higher
- Works on macOS, Linux, Windows (via `.venv`)
- Virtual environment setup with uv recommended

**Production/Deployment:**
- Python 3.12+ runtime
- Docker container support via `Dockerfile` (base: `python:3.12-slim`)
- Run command in Docker: `mcp run src/intervals_mcp_server/server.py`

## CI/CD

**GitHub Actions:**
- `.github/workflows/python-app.yml` - Python 3.12 tests on push/PR to main
  - Runs pytest with environment secrets (API_KEY) and variables (ATHLETE_ID)
- `.github/workflows/pylint.yml` - Pylint static analysis on all pushes
- `.github/workflows/stale.yml` - Stale issue management

---

*Stack analysis: 2026-04-24*
