# Intervals.icu MCP Server

Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for retrieving activities, events, and wellness data; creating and enriching climbing activities (with discipline, grades, RPE, and session focus); writing wellness entries (sleep, soreness, HRV, RHR, subjective metrics); and getting a single training-status report blending CTL/ATL/TSB load metrics with recent wellness signals.

If you find the Model Context Protocol (MCP) server useful, please consider supporting its continued development with a donation.

## Requirements

- Python 3.12 or higher
- [Model Context Protocol (MCP) Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- httpx
- python-dotenv

## Setup

### 1. Install uv (recommended)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone this repository

```bash
git clone https://github.com/mvilanova/intervals-mcp-server.git
cd intervals-mcp-server
```

### 3. Create and activate a virtual environment

```bash
# Create virtual environment with Python 3.12
uv venv --python 3.12

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 4. Sync project dependencies

```bash
uv sync
```

### 5. Set up environment variables

Make a copy of `.env.example` and name it `.env` by running the following command:

```bash
cp .env.example .env
```

Then edit the `.env` file and set your Intervals.icu athlete id and API key:

```
API_KEY=your_intervals_api_key_here
ATHLETE_ID=your_athlete_id_here
```

#### Getting your Intervals.icu API Key

1. Log in to your Intervals.icu account
2. Go to Settings > API
3. Generate a new API key

#### Finding your Athlete ID

Your athlete ID is typically visible in the URL when you're logged into Intervals.icu. It looks like:

- `https://intervals.icu/athlete/i12345/...` where `i12345` is your athlete ID

## Climbing setup — required Intervals.icu custom fields

The climbing tools (added in Phase 2+ of the climbing training loop) write
structured session data to Intervals.icu **custom activity fields**. Custom
fields cannot be created via the API — you must define them yourself, **once**,
in your Intervals.icu athlete settings, before the climbing tools will work.

Create each of the following fields exactly as specified (`Key` is the field's
internal name; `Type` is what you select in the Intervals.icu field editor;
`Options` are the exact option strings you enter for `select`-type fields):

| Key                   | Type    | Options                                                    |
|-----------------------|---------|------------------------------------------------------------|
| `discipline`          | select  | `bouldering`, `sport_lead`, `top_rope`, `trad`             |
| `indoor`              | bool    | —                                                          |
| `session_focus`       | select  | `power`, `endurance`, `technique`, `projecting`, `mileage` |
| `top_grade_sent`      | text    | —                                                          |
| `top_grade_attempted` | text    | —                                                          |
| `sends`               | integer | —                                                          |
| `attempts`            | integer | —                                                          |

**Important:**
- Option strings are **case-sensitive** — use lowercase_snake_case exactly as
  listed (e.g. `sport_lead`, not `Sport Lead` or `SPORT_LEAD`). The climbing
  tools compare option values with strict equality; a case or spacing mismatch
  will be silently ignored by Intervals.icu and the tool will refuse to write.
- `top_grade_sent` and `top_grade_attempted` are plain text fields. The
  climbing tools validate grades against the session's declared discipline —
  Font grades (uppercase, e.g. `6A`, `7B+`) for bouldering, French sport
  grades (lowercase, e.g. `6a`, `7b+`) for sport lead / top-rope / trad.

### Verifying the setup

After creating the fields, verify they are all present by asking Claude to
run the `verify_custom_fields_setup` MCP tool. It reports any missing fields
by name:

```
verify_custom_fields_setup()
```

If any required field is missing, the climbing write tools (Phase 2+) will
refuse to run against your account until the missing fields are added.

## Climbing tools

Once the custom fields are in place, the milestone ships five tools you call from Claude Desktop. Each tool's full parameter list lives in its docstring; the examples below are the most common shape.

### `write_wellness_entry`

Log a wellness entry for an athlete on a given date with any subset of sleep, soreness, fatigue, motivation, stress, HRV, and resting HR fields. Fields not supplied use upsert semantics — they do not clobber values already logged for that day.

Use it when you want to record subjective wellness for a date Garmin / Whoop / Oura did not auto-sync, or to add fields the wearable did not capture.

```text
write_wellness_entry(date="2026-04-28", sleep_hours=7.5, soreness=2)
```

### `enrich_activity_climbing`

Enrich an existing Intervals.icu activity (e.g. a Garmin-synced session) with climbing metadata and RPE — discipline, indoor/outdoor, session focus, grades, sends/attempts — and write the native `icu_rpe` field.

Use it when an activity is already on Intervals.icu (auto-imported or hand-created elsewhere) and you want to add climbing context after the fact.

```text
enrich_activity_climbing(activity_id="i12345", discipline="bouldering", indoor=True, top_grade_sent="6A+", sends=4, attempts=7, rpe=6)
```

### `create_climbing_activity`

Create a climbing activity from scratch on Intervals.icu — date, duration, title, plus optional climbing fields. The tool runs a duplicate guard (date + type) before posting so reconnects and retries do not double up.

Use it when there is no Garmin sync and no planned event for the session — the most common "I just climbed, log it" path.

```text
create_climbing_activity(date="2026-04-28", duration_minutes=90, discipline="sport_lead", indoor=False, top_grade_sent="6c+", rpe=7)
```

### `complete_climbing_session`

Complete a planned climbing event by creating a linked activity. The planned event stays on the calendar (with `paired_event_id` linkage) so weekly-plan adherence remains visible.

Use it when you scheduled a session in the Intervals.icu calendar and want to mark it done with the actual climbing metadata.

```text
complete_climbing_session(event_id="i98765", discipline="bouldering", session_focus="projecting", rpe=8)
```

### `get_training_status`

Return a plain-text training-status report blending CTL/ATL/TSB load metrics with recent sleep, soreness, fatigue, HRV/RHR — plus a data-quality flag if too many recent activities lack RPE.

Use it when you want a single "how should I train today?" answer without juggling separate dashboards.

```text
get_training_status()
```

## Updating

This project is actively developed, with new features and fixes added regularly. To stay up to date, follow these steps:

### 1. Pull the latest changes from `main`

> ⚠️ Make sure you don’t have uncommitted changes before running this command.

```bash
git checkout main && git pull
```

### 2. Update Python dependencies

Activate your virtual environment and sync dependencies:

```bash
source .venv/bin/activate
uv sync
```

### Troubleshooting

If Claude Desktop fails due to configuration changes, follow these steps:

1. Delete the existing entry in claude_desktop_config.json.
2. Reconfigure Claude Desktop from the intervals_mcp_server directory:

```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

## Usage with Claude

### 1. Configure Claude Desktop

To use this server with Claude Desktop, you need to add it to your Claude Desktop configuration.

1. Run the following from the `intervals_mcp_server` directory to configure Claude Desktop:

```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

2. If you open your Claude Desktop App configuration file `claude_desktop_config.json`, it should look like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/Users/<USERNAME>/.cargo/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with-editable",
        "/path/to/intervals-mcp-server",
        "mcp",
        "run",
        "/path/to/intervals-mcp-server/src/intervals_mcp_server/server.py"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Where `/path/to/` is the path to the `intervals-mcp-server` code folder in your system.

If you observe the following error messages when you open Claude Desktop, include the full path to `uv` in the command key in the `claude_desktop_config.json` configuration file. You can get the full path by running `which uv` in the terminal.

```
2025-04-28T10:21:11.462Z [info] [Intervals.icu MCP Server] Initializing server...
2025-04-28T10:21:11.477Z [error] [Intervals.icu MCP Server] spawn uv ENOENT
2025-04-28T10:21:11.477Z [error] [Intervals.icu MCP Server] spawn uv ENOENT
2025-04-28T10:21:11.481Z [info] [Intervals.icu MCP Server] Server transport closed
2025-04-28T10:21:11.481Z [info] [Intervals.icu MCP Server] Client transport closed
```

3. Restart Claude Desktop.

### 2. Use the MCP server with Claude

Once the server is running and Claude Desktop is configured, you can use the following tools to ask questions about your past and future activities, events, and wellness data.

- `get_activities`: Retrieve a list of activities
- `get_activity_details`: Get detailed information for a specific activity
- `get_activity_intervals`: Get detailed interval data for a specific activity
- `get_wellness_data`: Fetch wellness data
- `get_events`: Retrieve upcoming events (workouts, races, etc.)
- `get_event_by_id`: Get detailed information for a specific event

## Usage with ChatGPT

ChatGPT’s beta MCP connectors can also talk to this server over the SSE transport.

1. Start the server in SSE mode so it exposes the `/sse` and `/messages/` endpoints:

   ```bash
   export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 MCP_TRANSPORT=sse FASTMCP_LOG_LEVEL=INFO
   python src/intervals_mcp_server/server.py
   ```

   The startup log prints the full URLs (for example `http://127.0.0.1:8765/sse`). ChatGPT needs that public URL, so forward the port with a tool such as `ngrok http 8765` if you are not exposing the server directly.

2. In ChatGPT, open **Settings → Features → Custom MCP Connectors** and click **Add**. Fill in:

   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://<your-public-host>/sse`
   - **Authentication**: leave as _No authentication_ unless you have protected your tunnel.

   You can reuse the same `ngrok http 8765` tunnel URL here; just ensure it forwards to the host/port you exported above.

3. Save the connector and open a new chat. ChatGPT will keep the SSE connection open and POST follow-up requests to the `/messages/` endpoint announced by the server. If you restart the MCP server or tunnel, rerun the SSE command and update the connector URL if it changes.

## Development and testing

Install development dependencies and run the test suite with:

```bash
uv sync --all-extras
pytest -v tests
```

### Running the server locally

To start the server manually (useful when developing or testing), run:

```bash
mcp run src/intervals_mcp_server/server.py
```

#### Enabling debug logging

To capture server logs for debugging, wrap the command in a bash shell and redirect stderr to a file. Modify your `claude_desktop_config.json` like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "/Users/<USERNAME>/.local/bin/uv run --with 'mcp[cli]' --with-editable /path/to/intervals-mcp-server mcp run /path/to/intervals-mcp-server/src/intervals_mcp_server/server.py 2>> /path/to/intervals-mcp-server/mcp-server.log"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then tail the log file to see output in real-time:

```bash
tail -f /path/to/intervals-mcp-server/mcp-server.log
```

## License

The GNU General Public License v3.0

## Featured

### Glama.ai

<a href="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server/badge" alt="Intervals.icu Server MCP server" />
</a>
