# Phase 01 — Deferred Items

Items discovered during execution but out of scope for the current task.

## Pre-existing mypy errors in utils/formatting.py

**Discovered in:** Plan 01-01 (Task 3 verification step)

**Files:**
- `src/intervals_mcp_server/utils/formatting.py:28` — `Argument 1 to "add" of "set" has incompatible type "object"; expected "str"`
- `src/intervals_mcp_server/utils/formatting.py:358` — `"dict[str, Any]" has no attribute "accessed"`

**Status:** Pre-existing on `main` before Plan 01-01. Not caused by this plan (D-16/D-20 — formatting.py was not touched). Confirmed via `git stash` + baseline `uv run mypy src/intervals_mcp_server/utils/formatting.py`.

**Disposition:** Out of scope per executor scope-boundary rule. Plan 01-02 extends `formatting.py` with `format_climbing_activity` and may take the opportunity to fix these errors if it touches the file significantly — otherwise leave for a future cleanup pass.
