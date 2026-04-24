# Architecture

**Analysis Date:** 2026-04-24

## Pattern Overview

**Overall:** MCP (Model Context Protocol) Server using Async Request-Response Pattern

**Key Characteristics:**
- Standalone FastMCP server exposing tools to Claude Desktop and ChatGPT via multiple transports
- Async-first architecture with httpx for HTTP client communication
- Tool-based interface using decorator registration pattern
- Layered design with API abstraction, utilities, and domain-specific tools
- Config singleton pattern for environment management
- Graceful error handling with user-friendly messages

## Layers

**Entry Point Layer:**
- Purpose: Application bootstrap and transport initialization
- Location: `src/intervals_mcp_server/server.py`, `src/intervals_mcp_server/server_setup.py`
- Contains: Server startup logic, tool imports, configuration validation
- Depends on: FastMCP, config, tools, utilities
- Used by: MCP orchestration framework (Claude Desktop, ChatGPT)

**MCP Instance Layer:**
- Purpose: Shared FastMCP instance to avoid circular imports
- Location: `src/intervals_mcp_server/mcp_instance.py`
- Contains: FastMCP singleton with lifespan management
- Depends on: API client setup
- Used by: All tool modules for decorator registration

**Configuration Layer:**
- Purpose: Load and manage environment variables and config singleton
- Location: `src/intervals_mcp_server/config.py`
- Contains: Config dataclass, singleton pattern, environment loading
- Depends on: python-dotenv, validation utilities
- Used by: API client, all tool modules

**API Client Layer:**
- Purpose: HTTP communication with Intervals.icu API, error handling, client lifecycle
- Location: `src/intervals_mcp_server/api/client.py`
- Contains: `make_intervals_request()`, httpx client management, error mapping
- Depends on: httpx, config, logging
- Used by: All tool modules to query Intervals.icu

**Tool Layer:**
- Purpose: MCP tools exposed to Claude/ChatGPT for specific domains
- Location: `src/intervals_mcp_server/tools/` (activities.py, events.py, wellness.py, custom_items.py)
- Contains: Tool functions decorated with `@mcp.tool()`, business logic, data transformation
- Depends on: API client, config, utilities, types
- Used by: MCP server for tool invocation

**Utility Layer:**
- Purpose: Shared helpers for formatting, validation, date handling, type definitions
- Location: `src/intervals_mcp_server/utils/` (formatting.py, validation.py, dates.py, types.py)
- Contains: Data serialization, input validation, date parsing, type definitions
- Depends on: Standard library
- Used by: Tools, API client, config

## Data Flow

**Tool Invocation:**

1. Claude/ChatGPT invokes a tool (e.g., `get_activities`)
2. MCP server routes to decorated tool function in `src/intervals_mcp_server/tools/activities.py`
3. Tool validates inputs using `resolve_athlete_id()`, `resolve_date_params()` from `src/intervals_mcp_server/utils/validation.py`
4. Tool calls `make_intervals_request()` from `src/intervals_mcp_server/api/client.py`
5. API client adds auth (basic auth with API_KEY), headers, and sends async HTTP GET/POST/PUT to Intervals.icu
6. Response parsed and returned to tool
7. Tool formats response using formatters from `src/intervals_mcp_server/utils/formatting.py`
8. Formatted string returned to Claude/ChatGPT

**HTTP Request Flow:**

```
Tool Input
  ↓
Resolve Parameters (config defaults)
  ↓
make_intervals_request()
  ├─ Get config (API_KEY, base URL)
  ├─ Prepare headers, auth, body
  ├─ Get/recreate httpx.AsyncClient
  ├─ Send request (timeout 30s)
  └─ Retry on closed client
  ↓
Error Handling
  ├─ HTTP Status Error → mapped message
  ├─ Request Error → logged
  ├─ JSON decode error → error dict
  └─ Success → return parsed JSON
  ↓
Return to Tool
```

**State Management:**
- Config is singleton loaded once and cached
- httpx client is shared globally and reused across requests, recreated if closed
- MCP instance is created at module load and used for tool registration
- No per-request state; all requests are stateless

## Key Abstractions

**make_intervals_request():**
- Purpose: Unified HTTP client for all API communication
- Examples: `src/intervals_mcp_server/tools/activities.py`, `src/intervals_mcp_server/tools/events.py`
- Pattern: Async function returning dict/list or error dict; handles retry on closed client

**Config (Singleton):**
- Purpose: Environment-based configuration centralized and validated
- Examples: `src/intervals_mcp_server/config.py`
- Pattern: `get_config()` returns cached instance; validates on first load

**Tool Decorator Registration:**
- Purpose: FastMCP discovers tools via `@mcp.tool()` decorator
- Examples: All functions in `src/intervals_mcp_server/tools/*.py`
- Pattern: Decorator-based; tools auto-register when imported

**Data Types (Dataclasses):**
- Purpose: Type-safe representation of Intervals.icu domain objects
- Examples: `WorkoutDoc`, `Step`, `Value` in `src/intervals_mcp_server/utils/types.py`
- Pattern: Dataclass with `to_dict()`, `from_dict()`, `to_json()`, `from_json()` methods

**_KeyTracker:**
- Purpose: Track which fields are accessed during formatting to support optional fields
- Examples: `src/intervals_mcp_server/utils/formatting.py`
- Pattern: Dict subclass that records accessed keys for dynamic field detection

## Entry Points

**Server Bootstrap:**
- Location: `src/intervals_mcp_server/server.py`
- Triggers: `python src/intervals_mcp_server/server.py` or `mcp run src/intervals_mcp_server/server.py`
- Responsibilities: Load config, validate athlete ID, select transport, start MCP server

**Tool Registration:**
- Location: Tool modules in `src/intervals_mcp_server/tools/`
- Triggers: Import from `src/intervals_mcp_server/server.py`
- Responsibilities: Register tools with FastMCP via decorators upon import

**Transport Setup:**
- Location: `src/intervals_mcp_server/server_setup.py`
- Triggers: `setup_transport()` called in server.py
- Responsibilities: Parse `MCP_TRANSPORT` env var, validate, return transport alias

## Error Handling

**Strategy:** User-friendly error messages with detailed logging

**Patterns:**
- Validation errors: Caught early (athlete ID, dates) with clear messages
- HTTP errors: Mapped to friendly messages (401→check API key, 404→not found, etc.)
- Request errors: Logged with full detail, returned as error dict to tool
- JSON decode: Logged error, return error dict
- Closed client: Automatically retry by recreating httpx client
- Return error dicts: `{"error": True, "message": "...", "status_code": ...}` checked by tools

## Cross-Cutting Concerns

**Logging:** 
- Framework: Python standard logging
- Configuration: `src/intervals_mcp_server/server.py` sets INFO level, StreamHandler
- Usage: All modules log to "intervals_icu_mcp_server" logger with module-level getLogger

**Validation:** 
- Athlete ID: Regex match `i?\d+` or empty; checked on server startup and per-tool
- Dates: ISO YYYY-MM-DD format; parsed with datetime.strptime
- API responses: Type check (isinstance dict/list) before processing

**Authentication:** 
- Method: HTTP Basic Auth with username="API_KEY" and password=<api_key_value>
- Source: Config or per-tool parameter (parameter overrides config)
- Failure: 401 error → user-friendly message about API key

**Transport Layer:** 
- Supports: stdio (default), SSE, streamable-http
- Selection: `MCP_TRANSPORT` env var, mapped and validated in `setup_transport()`
- Lifecycle: FastMCP manages socket/HTTP connection; httpx client closed on shutdown via lifespan

---

*Architecture analysis: 2026-04-24*
