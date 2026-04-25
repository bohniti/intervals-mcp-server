# Phase 2: Wellness Write and Activity Enrichment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 02-wellness-write-and-activity-enrichment
**Areas discussed:** Resolve spike 422s first, write_wellness_entry API surface, enrich_activity_climbing design, Module placement + guard invocation

---

## Resolve spike 422s first

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted second probe, all three unknowns | Plan 02-01 is a focused script that resolves activity custom-field PUT shape, wellness fatigue/stress/motivation valid scale, and icu_rpe write path. Findings drive Plans 02-02 and 02-03. ~30 min, one script run. | ✓ |
| Probe activity-write only; assume wellness scales from docs | Probe only the activity custom-field PUT (highest-blast-radius unknown). Use intervals.icu forum / public docs to settle wellness field scales. Faster but residual risk on wellness writes. | |
| Skip probe, design defensively, fix on first 422 | Build with conservative assumptions; catch failures in tool tests + first manual smoke. Faster start, slower convergence. | |
| Re-run Phase 1 spike script extended in place | Add three more probe functions to scripts/spike_write_endpoints.py, re-run, append to 01-SPIKE-FINDINGS.md. Same artifact, no new file. Mixes Phase 1 closure with Phase 2 discovery. | |

**User's choice:** Targeted second probe, all three unknowns
**Notes:** Recommendation accepted. Plan 02-01 is the second-probe script.

| Option | Description | Selected |
|--------|-------------|----------|
| New 02-SPIKE-FINDINGS.md inside Phase 2 | Each phase owns its discovery artifacts. 02-SPIKE-FINDINGS.md sits alongside 02-CONTEXT.md and 02-RESEARCH.md. Phase 1 stays closed. | ✓ |
| Append to 01-SPIKE-FINDINGS.md | Keep all spike data in one file. Simpler to grep across phases, but blurs the phase boundary. | |

**User's choice:** New 02-SPIKE-FINDINGS.md inside Phase 2
**Notes:** Recommendation accepted.

| Option | Description | Selected |
|--------|-------------|----------|
| Stop and re-discuss | If no body shape lands custom fields, pause Phase 2, escalate. The milestone may need a Key Decision change. Don't ship a half-broken tool. | ✓ |
| Fall back to writing climbing fields into description as structured text | Encode climbing payload as JSON/YAML in description. Queryable via free-text only; not in trend reports. | |
| Ship icu_rpe only, defer custom-field writes to v2 | Ship enrich_activity_climbing as RPE-only. Defer CLIMB-04/05/06. Significant scope cut. | |

**User's choice:** Stop and re-discuss
**Notes:** Hard-stop fallback. Don't unilaterally invalidate a Key Decision.

---

## write_wellness_entry API surface

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit named params, no escape hatch | One Optional param per supported field (sleep_hours, sleep_quality, soreness, fatigue, motivation, stress, mood, hrv, resting_hr). Type-safe, strong docstring. New fields require signature change. | ✓ |
| Explicit common params + extra_fields dict | Same explicit params plus extra_fields: dict for any other Intervals.icu wellness field. Trades type safety for forward flexibility. | |
| Single metrics dict | Flexible, no per-field validation, weakest docstring guidance. Likely Pitfall #6. | |

**User's choice:** Explicit named params, no escape hatch
**Notes:** Selected with preview confirmed (full async signature shown in question preview).

| Option | Description | Selected |
|--------|-------------|----------|
| Hard 1-4 validation locked from spike findings | Probe-confirmed ranges encoded as constants. Reject out-of-range with clear error before PUT. Range table in utils/wellness.py. | ✓ |
| Soft validation — warn but pass through | Log warning if outside range, still send to API. | |
| No client-side range validation, let the API 422 | Trust API to reject; opaque 422s. Fights the Phase 1 ethos. | |

**User's choice:** Hard 1-4 validation locked from spike findings
**Notes:** Range constants derived from Plan 02-01 results.

| Option | Description | Selected |
|--------|-------------|----------|
| User-friendly units in, API units inside | sleep_hours: float on the public API; internal sleepSecs = int(sleep_hours * 3600). Document in docstring. | ✓ |
| Pass-through API units | Tool param matches API field/unit (sleepSecs: int). Zero translation; Claude does math. | |
| Both — accept either with explicit suffix in name | Accept either; tool picks non-None. Doubles params. | |

**User's choice:** User-friendly units in, API units inside

| Option | Description | Selected |
|--------|-------------|----------|
| Drop None-valued params from PUT body before send | body = {k: v for k, v in candidates.items() if v is not None}. Preserves upsert. No explicit clear in v1. | ✓ |
| Drop None + provide an explicit clear flag | Same plus clear_fields list. Adds footgun for no v1 use case. | |

**User's choice:** Drop None-valued params from PUT body before send

---

## enrich_activity_climbing design

| Option | Description | Selected |
|--------|-------------|----------|
| activity_id required, all climbing fields optional, at-least-one-supplied check | discipline required if any grade is set. override: bool = False is part of signature. | ✓ |
| activity_id + discipline both required, rest optional | Force discipline upfront. Slightly safer, slightly less flexible. | |
| Single climbing_data: dict[str, Any] payload | Loses per-field type safety; weak docstring. | |

**User's choice:** activity_id required, all climbing fields optional, at-least-one-supplied check
**Notes:** Full signature confirmed via preview.

| Option | Description | Selected |
|--------|-------------|----------|
| Default-deny, explicit override=True flag | Pre-PUT GET; if any supplied field has non-null prior AND override is False, refuse. override=True writes + adds activity_message recording prior values. | ✓ |
| Default-allow with audit message every time | Always overwrite, always append message. Lower friction, easier to lose history. | |
| Default-deny, no override at all | Refuse re-enrichment entirely; user must clear via UI. Strictest, blocks corrections. | |
| No re-enrichment guard — always overwrite, no message | Cheapest. Loses Pitfall #10 mitigation. | |

**User's choice:** Default-deny, explicit override=True flag
**Notes:** Audit message goes through add_activity_message — Intervals.icu's own log, no shadow store.

| Option | Description | Selected |
|--------|-------------|----------|
| Readback only the fields the user supplied; error if any are missing/wrong | After PUT, GET /activity/{id}; confirm each supplied field appears with the value sent. Cheap, precise, catches Pitfall #2. | ✓ |
| Readback all 7 custom fields + icu_rpe, regardless of what was sent | Confirms entire climbing state. Noisier and slower. Over-engineered for v1. | |
| Skip readback if verify_custom_fields_setup passed at start of call | Conflates definition existence with write success. Don't. | |

**User's choice:** Readback only the fields the user supplied; error if any are missing/wrong

| Option | Description | Selected |
|--------|-------------|----------|
| Same PUT, single body, single readback — contingent on probe | If probe confirms icu_rpe + custom fields can travel in one PUT, do that. If not, fall back to two-write design with explicit partial-failure surfacing. | ✓ |
| Always two separate PUTs regardless of probe | Decouple icu_rpe from custom fields. More API calls, partial-failure complexity. | |
| Defer icu_rpe to a separate dedicated tool | set_activity_rpe as own MCP tool. Two calls for common case; fights "single-shot, all fields". | |

**User's choice:** Same PUT, single body, single readback — contingent on probe

---

## Module placement + guard invocation

| Option | Description | Selected |
|--------|-------------|----------|
| tools/wellness.py — semantic fit | Wellness writes are not climbing-specific (WELL-01/02/03 are general). Existing 71-line wellness.py absorbs the new tool well. tools/climbing.py stays climbing-only. | ✓ |
| tools/climbing.py — single-domain Phase 2 module | Both Phase 2 tools in one place. Pro: bundles the milestone story. Con: file becomes mixed-domain. | |

**User's choice:** tools/wellness.py — semantic fit

| Option | Description | Selected |
|--------|-------------|----------|
| New utils/wellness.py module | Houses range table + unit converters + drop-None body builder. Mirrors utils/grades.py + utils/climbing.py split. Keeps utils/climbing.py climbing-only. | ✓ |
| Add wellness ranges to utils/climbing.py | One fewer file but mixes domains. Fights D-16 (Phase 1). | |
| Inline constants in tools/wellness.py | Simplest; loses utils/* discoverability; tests have to import from tool module. | |

**User's choice:** New utils/wellness.py module

| Option | Description | Selected |
|--------|-------------|----------|
| Only when the call writes at least one custom field | If only rpe is supplied (native field), skip the guard. If any custom-field param is supplied, run the guard before PUT and hard-block. | ✓ |
| Always fire on every enrich call | Extra GET per write, simple invariant. | |
| Try the write, run guard only on 422 fallback | Cheapest happy path; mixes write semantics with discovery; fights D-12 (Phase 1). | |

**User's choice:** Only when the call writes at least one custom field

| Option | Description | Selected |
|--------|-------------|----------|
| No — wellness writes use native Intervals.icu fields, not custom fields | Wellness fields are all native; the verify gate exists to protect climbing custom-field writes from silent failure (Pitfall #2). Add a one-line code comment so future-Claude doesn't add it back. | ✓ |
| Yes — fire it for symmetry with enrich_activity_climbing | Symmetry vs unnecessary work. Adds an API call per wellness write for no protection. | |

**User's choice:** No — wellness writes use native Intervals.icu fields, not custom fields

---

## Claude's Discretion

- Exact wellness API field-name mapping (`mood` vs `feel`, etc.) — confirm from Phase 1 spike's wellness response and lock in `_PARAM_TO_API_FIELD`.
- Whether the second probe extends `scripts/spike_write_endpoints.py` or creates `scripts/spike_write_endpoints_phase2.py`.
- Exact mechanics of `add_activity_message` for the override audit trail.
- Order of arguments in `enrich_activity_climbing` after `activity_id`.
- Whether enrich-tool tests grow `tests/test_climbing.py` or get a new `tests/test_climbing_write.py` file.
- Whether to wire any user-friendly `feel` parameter (currently not in scope).

## Deferred Ideas

- Explicit wellness clear-field mechanism (`clear_fields` param)
- `extra_fields` escape hatch for wellness writes
- Improving the verify-fields readback heuristic (Phase 1 known limitation)
- Auto-generating docstring / wellness range table from a single source
- Status-tool-side data-quality flag for missing wellness fields (Phase 4 concern)
- Generic non-climbing manual-activity creation tool (`write_activity`) — v2 GEN-v2-01
- Finger / skin condition wellness field — v2 CLIMB-v2-01
- Dedicated `set_activity_rpe` tool (rejected; icu_rpe rides inside enrich_activity_climbing)
