# Structure

**Analysis Date:** 2026-04-24

## Directory Layout

```
intervals-mcp-server/
├── src/
│   └── intervals_mcp_server/          # Main package (importable)
│       ├── __init__.py                 # Package init
│       ├── server.py                   # Entry point — bootstrap + transport start
│       ├── server_setup.py             # Transport selection helpers
│       ├── mcp_instance.py             # Shared FastMCP singleton
│       ├── config.py                   # Config dataclass + singleton loader
│       ├── py.typed                    # PEP 561 marker (typed package)
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py               # HTTP client — make_intervals_request()
│       ├── tools/                      # MCP tools grouped by domain
│       │   ├── __init__.py
│       │   ├── activities.py           # Activities/workouts tools
│       │   ├── events.py               # Calendar events tools
│       │   ├── wellness.py             # Wellness data tools
│       │   └── custom_items.py         # Custom items tools
│       └── utils/                      # Shared helpers
│           ├── dates.py                # Date parsing + defaults
│           ├── formatting.py           # Response formatters (uses _KeyTracker)
│           ├── types.py                # Dataclasses: WorkoutDoc, Step, Value
│           └── validation.py           # Input validation (athlete ID, dates)
├── tests/
│   ├── __init__.py
│   ├── sample_data.py                  # Test fixtures / sample payloads
│   ├── test_server.py                  # Server + tool integration tests
│   ├── test_formatting.py              # Formatter unit tests
│   ├── test_make_intervals_request.py  # API client tests
│   ├── test_value.py                   # Value dataclass tests
│   └── ressources/                     # Test resource files (note: "ressources" spelling)
│       ├── wellness_entry.json
│       └── wellness_entry_formatted.txt
├── pyproject.toml                      # Package + tooling config (hatch, ruff, mypy, pytest)
├── uv.lock                             # uv dependency lockfile
├── Dockerfile                          # Container image definition
├── MANIFEST.in                         # Source distribution manifest
├── README.md                           # User-facing documentation
├── CONTRIBUTING.md                     # Contribution guidelines
├── AGENTS.md                           # Agent/LLM instructions
└── LICENSE                             # GPL-3.0-only
```

## Key Locations

**Entry point:**
- `src/intervals_mcp_server/server.py` — Main executable. Configures logging, validates athlete ID on startup, imports tool modules (triggering decorator registration), and starts the FastMCP server with the configured transport.

**Shared FastMCP instance:**
- `src/intervals_mcp_server/mcp_instance.py` — The single `FastMCP` object that all tool modules decorate against. Exists in its own module to break circular imports between `server.py` and the tool modules.

**Configuration:**
- `src/intervals_mcp_server/config.py` — `Config` dataclass and `get_config()` singleton. Loads environment via python-dotenv.
- `.env` / `.env.example` — Runtime environment (API_KEY, ATHLETE_ID, MCP_TRANSPORT, etc.).

**HTTP surface:**
- `src/intervals_mcp_server/api/client.py` — The one function (`make_intervals_request()`) every tool calls to talk to Intervals.icu. Centralizes auth, retries on a closed httpx client, and error mapping.

**Tool domains** (`src/intervals_mcp_server/tools/`):
- `activities.py` — Activity list/detail, intervals, streams, workout docs.
- `events.py` — Calendar events, planned workouts.
- `wellness.py` — Wellness entries, fitness/fatigue/form, training load.
- `custom_items.py` — Custom user-defined items.

Each tool module imports `mcp` from `mcp_instance` and registers functions via `@mcp.tool()`.

**Utilities** (`src/intervals_mcp_server/utils/`):
- `formatting.py` — Response-to-string formatters. Uses `_KeyTracker` (a dict subclass) to auto-detect which fields are present.
- `validation.py` — `resolve_athlete_id()`, `resolve_date_params()`, input validators.
- `dates.py` — Date parsing helpers, default date windows.
- `types.py` — Domain dataclasses (`WorkoutDoc`, `Step`, `Value`) with `to_dict`/`from_dict`/`to_json`/`from_json`.

**Tests:**
- `tests/test_server.py` — Integration-style tests covering tool registration and end-to-end tool invocation.
- `tests/test_make_intervals_request.py` — HTTP client behavior (success, errors, retry).
- `tests/test_formatting.py` — Formatter output stability.
- `tests/test_value.py` — Dataclass serialization roundtrips.
- `tests/sample_data.py` — Reusable payload fixtures.
- `tests/ressources/` — File-based fixtures (**note spelling**: `ressources`, not `resources`).

**Packaging:**
- `pyproject.toml` — Hatchling build backend. Wheel packages `src/intervals_mcp_server`. Dev extras include pytest, mypy, ruff, pytest-asyncio, pre-commit, hatch, pytest-mock.
- `uv.lock` — Locked dependency graph (project uses `uv` for installs).
- `MANIFEST.in` — Extra files to include in sdist.
- `Dockerfile` — Container entry point for running the MCP server.

## Naming Conventions

**Packages / modules:**
- `snake_case` for all module and package names (`intervals_mcp_server`, `mcp_instance`, `custom_items`).
- Single-word module names preferred when unambiguous (`client.py`, `config.py`, `formatting.py`).

**Files:**
- Source files: `snake_case.py` (e.g., `make_intervals_request` is a function, but the test file is `test_make_intervals_request.py`).
- Test files: `test_<module>.py` mirroring the module under test.
- Fixtures / sample payloads: `sample_data.py`, resource files under `tests/ressources/`.

**Functions:**
- `snake_case`, verb-first when actions (`make_intervals_request`, `resolve_athlete_id`, `format_wellness_entry`).
- Getter-style for lookups (`get_config`, `get_activities`).
- Tool functions registered via `@mcp.tool()` follow the same convention.

**Classes:**
- `PascalCase` for dataclasses and classes (`Config`, `WorkoutDoc`, `Step`, `Value`).
- Private helpers prefixed with `_` (`_KeyTracker`).

**Constants:**
- `UPPER_SNAKE_CASE` (e.g., `API_KEY`, `ATHLETE_ID`, `MCP_TRANSPORT` env keys).

**Private / internal:**
- Leading underscore for module-private helpers (`_KeyTracker` in `utils/formatting.py`).

**Tool-layer grouping:**
- Tools are grouped into modules by **domain** (activities, events, wellness, custom_items), not by verb. New tools for an existing domain extend the matching module rather than creating a new one.

## Import Rules

- `mcp_instance.py` is the **only** module that constructs `FastMCP`. All tool modules import `mcp` from it — never construct a new instance.
- `config.py` exposes `get_config()`; callers should not instantiate `Config` directly.
- `api/client.py`'s `make_intervals_request()` is the single HTTP boundary — tools should not call `httpx` directly.
- Utilities in `utils/` are leaf dependencies: they import only from stdlib and each other, never from `tools/` or `api/`.

## Where To Add New Code

| Need | Goes in |
|------|---------|
| New MCP tool for existing domain | Extend the matching module in `src/intervals_mcp_server/tools/` |
| New MCP tool for a new domain | New module in `src/intervals_mcp_server/tools/`, import into `server.py` |
| New response formatter | `src/intervals_mcp_server/utils/formatting.py` |
| New input validator | `src/intervals_mcp_server/utils/validation.py` |
| New domain dataclass | `src/intervals_mcp_server/utils/types.py` |
| New HTTP behavior (retry, header) | `src/intervals_mcp_server/api/client.py` |
| New env var | `src/intervals_mcp_server/config.py` (+ `.env.example`) |
| New transport | `src/intervals_mcp_server/server_setup.py` |
| New test | `tests/test_<module>.py` mirroring source file |

---

*Structure analysis: 2026-04-24*
