# Phase 1: Foundation and Write-Path Spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 01-foundation-and-write-path-spike
**Areas discussed:** Spike execution + cleanup, Grade/discipline validation model, Custom-field prerequisite system, Climbing utility layout + formatter stubs

---

## Spike execution + cleanup

### How should the live API spike be executed?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone async script | `scripts/spike_write_endpoints.py`, `uv run`, uses `make_intervals_request()`, commits to repo | ✓ |
| Pytest integration test (opt-in marker) | `tests/integration/test_write_spike.py` with `@pytest.mark.live`, run with `pytest -m live` | |
| Ad-hoc REPL session | `python -i`, paste findings manually | |

**User's choice:** Standalone async script (recommended)
**Notes:** Easiest to re-run, doesn't pollute CI test runs, and the spike is a probe not a test.

### How should spike writes avoid polluting real training data?

| Option | Description | Selected |
|--------|-------------|----------|
| Far-future test date + delete after | Write to 2099-01-01, read back, delete/blank; fall back to manual cleanup list if no delete endpoint | ✓ |
| Keep as real first entries | Write to today, leave as real data | |
| Dry-run first, then opt-in real write | `--commit` flag to flip from log-only to real write | |

**User's choice:** Far-future test date + delete after (recommended)
**Notes:** Manual cleanup checklist goes into SPIKE-FINDINGS.md if the delete endpoint is not available.

### Where do spike findings live?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase dir SPIKE-FINDINGS.md | `.planning/phases/01-.../01-SPIKE-FINDINGS.md` | ✓ |
| `.planning/research/` addendum | Append to existing research docs | |
| Inline docstrings in client.py / tool modules | Document at call sites | |

**User's choice:** Phase dir SPIKE-FINDINGS.md (recommended)
**Notes:** Canonical Phase 1 output, referenced by Phase 2/3 planners.

---

## Grade/discipline validation model

### How should grade validation be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Regex + typed helpers | FONT_RE, FRENCH_SPORT_RE + `validate_grade(grade, discipline)` raising ValueError | ✓ |
| Enum of valid grades | Pre-enumerate all grades per scale as enum members | |
| Parser to structured object | `parse_grade('6A+') -> Grade(...)` enabling comparison/arithmetic | |

**User's choice:** Regex + typed helpers (recommended)
**Notes:** Small surface, easy to extend to v2 scales, no over-engineering.

### How strict on format — case, modifiers, and in-betweens?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict case + bare modifiers | Font uppercase, French sport lowercase, `+` allowed, no slashes/descriptors | ✓ |
| Strict case, no +/- modifiers | Reject any modifier in v1 | |
| Lenient — coerce case | Normalize case based on discipline | |

**User's choice:** Strict case + bare modifiers (recommended)
**Notes:** Case **is** the cross-scale guard — do not normalize. `+` is routine for climbers.

### How should discipline + indoor/outdoor be represented in types?

| Option | Description | Selected |
|--------|-------------|----------|
| StrEnum discipline + separate indoor bool | `Discipline` with 4 members + `indoor: bool` parameter | ✓ |
| Compound StrEnum with 8 values | `GYM_BOULDERING, OUTDOOR_BOULDERING, ...` single parameter | |
| Literal union (no enum class) | `Literal['bouldering', ...]` | |

**User's choice:** StrEnum discipline + separate indoor bool (recommended)
**Notes:** Each axis has one job; avoids combinatorial explosion.

### Where does 'session focus' live as a type?

| Option | Description | Selected |
|--------|-------------|----------|
| StrEnum alongside Discipline | Same module, same shape as Discipline | ✓ |
| Free-text string with validator | Accept any string, validate against allow-list | |
| You decide | Claude picks based on existing enum patterns | |

**User's choice:** StrEnum alongside Discipline (recommended)
**Notes:** Consistent with Discipline; tool parameter validated at boundary.

---

## Custom-field prerequisite system

### Which custom-field key convention should Phase 1 pin?

| Option | Description | Selected |
|--------|-------------|----------|
| Lowercase underscore, unprefixed | `discipline`, `session_focus`, `top_grade_sent`, ... | ✓ |
| `climbing_`-prefixed namespace | `climbing_discipline`, `climbing_session_focus`, ... | |
| PascalCase display names, snake_case keys | UI-display vs key separation | |
| You decide after spike | Defer until spike confirms | |

**User's choice:** Lowercase underscore, unprefixed (recommended)
**Notes:** 7 fields pinned: `discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`. Select-option strings must align with Discipline/SessionFocus StrEnum `.value`s.

### What surface should verify_custom_fields_setup expose?

| Option | Description | Selected |
|--------|-------------|----------|
| MCP tool + internal helper, both | One implementation, two call sites | ✓ |
| MCP tool only | User/Claude explicitly calls; writes rely on post-write readback | |
| Internal helper only | Runs transparently on first write, no Claude-visible tool | |

**User's choice:** MCP tool + internal helper, both (recommended)
**Notes:** User can preflight before first session; every write tool uses it as a guard.

### When a required field is missing, how strict should write tools be?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard block with named-field error | Refuse write, list missing fields, link to README | ✓ |
| Warn and proceed, readback-verify | Do write, report missing fields after the fact | |
| Partial — block only for affected fields | Per-field granularity | |

**User's choice:** Hard block with named-field error (recommended)
**Notes:** Pitfall #2 is a data-loss class failure; we refuse silent success.

### Where does the custom-field setup documentation live?

| Option | Description | Selected |
|--------|-------------|----------|
| README section + verify tool docstring | One source, mirrored in tool docstring so Claude has it in context | ✓ |
| Dedicated docs/SETUP-CLIMBING.md | Separate file, README links | |
| All three | README + dedicated doc + tool docstring | |

**User's choice:** README section + verify tool docstring (recommended)
**Notes:** Two in-sync locations is the sweet spot; a dedicated doc is premature.

---

## Climbing utility layout + formatter stubs

### Which utility files should Phase 1 create?

| Option | Description | Selected |
|--------|-------------|----------|
| grades.py + climbing.py | `utils/grades.py` (regex + validate_grade), `utils/climbing.py` (enums + CUSTOM_FIELD_KEYS) | ✓ |
| Single utils/climbing.py | Everything climbing-related in one file | |
| Extend utils/types.py + utils/validation.py | Fold into existing utility modules | |

**User's choice:** grades.py + climbing.py (recommended)
**Notes:** Grade math isolated for v2 scale extension; climbing domain types grouped.

### What does 'formatter stubs' mean for Phase 1?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal real formatter, Phase 2 extends | `format_climbing_activity()` renders Phase 1 fields; Phase 2 adds more | ✓ |
| Empty placeholder function | `raise NotImplementedError` | |
| No formatter in Phase 1 | Defer to Phase 2 entirely | |

**User's choice:** Minimal real formatter, Phase 2 extends (recommended)
**Notes:** Lets the spike render its own readback end-to-end.

### Where do the custom-field keys live as constants?

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen dict/dataclass in utils/climbing.py | `CUSTOM_FIELD_KEYS: Final[dict[str, FieldSpec]]` | ✓ |
| Plain string constants | `DISCIPLINE_KEY = 'discipline'`, etc. | |
| You decide | Claude picks based on existing patterns | |

**User's choice:** Frozen dict/dataclass in utils/climbing.py (recommended)
**Notes:** Single source of truth for verify tool, write tools, and README table.

---

## Claude's Discretion

Noted in CONTEXT.md:
- Exact regex bounds for top-end grades
- Readback retry / timing for verify-on-write
- Log level for spike script
- FieldSpec as `@dataclass(frozen=True)` vs `NamedTuple`

## Deferred Ideas

- V-scale / YDS grade support (v2)
- Grade-rank comparison/arithmetic (v2)
- Finger/skin, venue custom fields (v2)
- Auto-generating README field table from `CUSTOM_FIELD_KEYS`
- Activity delete endpoint confirmation (spike output determines)
