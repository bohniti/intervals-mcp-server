# Phase 01 — Deferred Items

Items discovered during Phase 01 execution that are out of scope for the current plan.

## Pre-existing mypy errors in `src/intervals_mcp_server/utils/formatting.py`

Discovered during Plan 01-02 (`format_climbing_activity` append). Confirmed pre-existing by
stashing my additive change and re-running mypy — both errors were already present on the
parent commit `8029fd5`.

```
src/intervals_mcp_server/utils/formatting.py:28: error: Argument 1 to "add" of "set" has incompatible type "object"; expected "str"  [arg-type]
src/intervals_mcp_server/utils/formatting.py:358: error: "dict[str, Any]" has no attribute "accessed"  [attr-defined]
```

- **Line 28** — `_KeyTracker.__contains__` takes `key: object` (to satisfy the dict ABC) but
  then passes it to `self.accessed: set[str]`.
- **Line 358** — `format_wellness_entry` rebinds `entries` to either the original dict or a
  `_KeyTracker`; mypy narrows on the parameter type and loses the `.accessed` attribute when
  `include_all_fields=True`.

**Scope:** D-16 and D-20 / Pitfall #12 forbid touching existing shared utilities in Phase 1,
and the scope-boundary rule forbids auto-fixing pre-existing issues unrelated to the current
task. Both fixes require modifying code outside the 01-02 task boundary.

**Deferred to:** A future dedicated typing-cleanup plan (likely Phase 5 wiring/polish, or a
separate maintenance plan) that can touch `_KeyTracker` and `format_wellness_entry` without
regressing the Pitfall #12 guard.
