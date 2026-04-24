# External Integrations

**Analysis Date:** 2026-04-24

## APIs & External Services

**Intervals.icu REST API:**
- Service: Intervals.icu athlete training platform
- What it's used for: Complete athlete data access (activities, events, wellness metrics, custom items, workouts)
  - SDK/Client: Custom async wrapper using httpx in `src/intervals_mcp_server/api/client.py`
  - Auth: HTTP Basic Auth with username `API_KEY` and password from `API_KEY` environment variable
  - Base URL: Configurable via `INTERVALS_API_BASE_URL` (defaults to `https://intervals.icu/api/v1`)
  - Timeout: 30 seconds per request

**Intervals.icu API Endpoints Used:**
- Activities: `/athlete/{id}/activities` - List, retrieve, add messages to activities
- Activity Details: `/athlete/{id}/activity/{activity_id}` - Detailed activity data
- Activity Intervals: `/athlete/{id}/activity/{activity_id}/intervals` - Performance intervals
- Activity Streams: `/athlete/{id}/activity/{activity_id}/streams` - Time-series sensor data
- Events: `/athlete/{id}/events` - Calendar events management (get, create, delete)
- Wellness: `/athlete/{id}/wellness` - Wellness metrics (sleep, stress, weight, HR, etc.)
- Custom Items: `/athlete/{id}/custom_items` - Custom data tracking (create, read, update, delete)

## Data Storage

**Databases:**
- Not applicable - This is a stateless API proxy server

**File Storage:**
- Local filesystem only - No persistent storage
- `.env` file for local configuration (not committed to git per `.gitignore`)
- `.env.example` for documentation of required environment variables

**Caching:**
- None - All requests are passed through to Intervals.icu API without caching

## Authentication & Identity

**Auth Provider:**
- Intervals.icu API Key Authentication
  - Approach: HTTP Basic Authentication
  - Implementation in `src/intervals_mcp_server/api/client.py` function `_prepare_request_config()`
  - Username: Hardcoded string `"API_KEY"`
  - Password: From environment variable `API_KEY` (loaded in `src/intervals_mcp_server/config.py`)
  - Fallback: Can pass `api_key` parameter to individual tool functions
  - Config location: `src/intervals_mcp_server/config.py` - `Config` dataclass and `load_config()` function

**Athlete Identification:**
- Athlete ID from environment variable `ATHLETE_ID` or per-tool parameter
- Validated in `src/intervals_mcp_server/utils/validation.py` - `validate_athlete_id()` function
- Format: String identifier (e.g., `i12345`)

## Monitoring & Observability

**Error Tracking:**
- None - Errors returned as structured dicts with `error: true` field

**Logs:**
- Python standard logging module
- Logger name: `intervals_icu_mcp_server`
- Configuration in `src/intervals_mcp_server/server.py`
  - Level: INFO
  - Handler: StreamHandler to stdout
- Specific logging in `src/intervals_mcp_server/api/client.py` for HTTP errors and client state

## CI/CD & Deployment

**Hosting:**
- No default hosting - Designed to run locally or in Docker containers
- Docker image available via `Dockerfile` (Python 3.12-slim)
- CLI invocation: `mcp run src/intervals_mcp_server/server.py`

**CI Pipeline:**
- GitHub Actions
  - `.github/workflows/python-app.yml` - Tests on Python 3.12
  - `.github/workflows/pylint.yml` - Linting on all pushes
  - Environment: `intervals-mcp-server-env` for secrets

## Environment Configuration

**Required env vars:**
- `API_KEY` - Intervals.icu API key (obtained from account settings)
- `ATHLETE_ID` - Athlete ID (visible in Intervals.icu URLs, e.g., `i12345`)

**Optional env vars:**
- `INTERVALS_API_BASE_URL` - API base URL (defaults to `https://intervals.icu/api/v1`)
- `MCP_TRANSPORT` - MCP transport type: `stdio` (default), `sse`, `http`, `streamable-http`
- `MCP_SSE_MOUNT_PATH` - Mount path for SSE transport

**Secrets location:**
- GitHub Actions: `secrets.API_KEY` (protected in Actions environment)
- Local: `.env` file (in `.gitignore`, not committed)
- Local template: `.env.example` for documentation

## Webhooks & Callbacks

**Incoming:**
- None - This is a read/write API client, not a webhook server

**Outgoing:**
- None - All communication is synchronous request/response to Intervals.icu API

## Transport Protocols

**MCP Transport Options:**
Supported in `src/intervals_mcp_server/server_setup.py` via `TransportAliases` enum and `setup_transport()`:
- `stdio` - Standard input/output (default, used by Claude Desktop)
- `sse` - Server-Sent Events (requires `MCP_SSE_MOUNT_PATH` env var)
- `streamable-http` - Streamable HTTP transport (mapped from `http` alias)
- Configured via `MCP_TRANSPORT` environment variable

**HTTP Configuration:**
- Async client: `httpx.AsyncClient` in `src/intervals_mcp_server/api/client.py`
- Connection pooling: Single shared client instance (module-level singleton)
- Request timeout: 30 seconds
- Automatic client recreation: If upstream closes connection mid-operation
- Error handling: Comprehensive HTTP status error mapping with user-friendly messages

## Tools/Features Exposed to Claude

**Activity Tools (in `src/intervals_mcp_server/tools/activities.py`):**
- `get_activities` - List athlete activities with optional date range filtering
- `get_activity_details` - Detailed data for single activity
- `get_activity_intervals` - Performance intervals from activity
- `get_activity_streams` - Sensor data (power, HR, cadence, etc.) from activity
- `get_activity_messages` - Messages/comments on activity
- `add_activity_message` - Add comment to activity

**Event Tools (in `src/intervals_mcp_server/tools/events.py`):**
- `get_events` - List calendar events
- `get_event_by_id` - Details for specific event
- `add_or_update_event` - Create or modify event
- `delete_event` - Delete single event
- `delete_events_by_date_range` - Batch delete events in date range

**Wellness Tools (in `src/intervals_mcp_server/tools/wellness.py`):**
- `get_wellness_data` - Sleep, weight, HR, stress, and custom metrics

**Custom Items Tools (in `src/intervals_mcp_server/tools/custom_items.py`):**
- `get_custom_items` - List custom tracked metrics
- `get_custom_item_by_id` - Single metric details
- `create_custom_item` - Create new custom metric
- `update_custom_item` - Modify custom metric
- `delete_custom_item` - Delete custom metric

---

*Integration audit: 2026-04-24*
