# Phase 4: Training Status Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 04-training-status-report
**Areas discussed:** Report shape & readiness framing, Data sources & TSB & windows, RPE data-quality, Token budget & empty-data handling

---

## Report Shape & Readiness Framing

### How should "today's readiness" be presented?

| Option | Description | Selected |
|--------|-------------|----------|
| TSB number + verbal band | Show TSB value AND a label (Fresh/Balanced/Fatigued/etc.) | ✓ |
| TSB number only | Just the raw number; let Claude do verbal framing | |
| Verbal band only | Just the label, hide the number | |

### What's the section structure?

| Option | Description | Selected |
|--------|-------------|----------|
| Today → This Week → Long-Term Trend | Three labeled sections in success-criteria order | ✓ |
| Single dense paragraph | All numbers in one flowing paragraph | |
| Today first, weekly+trend collapsed below | Lead with verdict, compact tail | |

### Plain text or minimal markdown?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal markdown headings + bullets | `## Today / ## This Week / ## Long-Term Trend` with bullets | ✓ |
| Plain text with line breaks | No markdown; section labels in caps | |
| Structured key-value blocks | `CTL: 42.1 \| ATL: 38.7 \| TSB: 3.4` style | |

### TSB band thresholds?

| Option | Description | Selected |
|--------|-------------|----------|
| Standard | TSB >25 burnt-out, 5-25 fresh, -10 to 5 balanced, -25 to -10 fatigued, <-25 risk | ✓ |
| Tighter / climbing-tuned | Widen Balanced; |TSB|>15 as edge | |
| Conservative (high-recovery) | Bias toward warning earlier | |

---

## Data Sources, TSB Computation & Time Windows

### Where do CTL/ATL come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Wellness daily entries | Single GET `/athlete/{id}/wellness?oldest=...&newest=...` for the whole window | ✓ |
| Per-activity icu_ctl / icu_atl | Read each activity; sparse on rest days | |
| Both — cross-validate | Read both, warn on mismatch | |

### How is TSB computed?

| Option | Description | Selected |
|--------|-------------|----------|
| Compute as CTL - ATL | Standard formula; explicit math | ✓ |
| Read 'tsb' field if present, fall back to compute | Future-proof for API expansion | |

### What time windows for each section?

| Option | Description | Selected |
|--------|-------------|----------|
| Weekly=7d / Long-term=42d / RPE-coverage=14d | Matches success criteria; 42d covers a 6-week training block | ✓ |
| Weekly=7d / Long-term=28d / RPE-coverage=14d | Shorter trend; lighter payload | |
| Weekly=7d / Long-term=90d / RPE-coverage=28d | Wider trend (~3 months); larger token cost | |

### Hardcoded vs optional override params?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded for v1 | Simpler signature; consistent shape | ✓ |
| Optional override params | weekly_window_days etc. as Optional[int] | |

### What if today's wellness entry is missing?

| Option | Description | Selected |
|--------|-------------|----------|
| Walk back to most recent entry within 7 days | Use latest within window; note "Latest fitness data: N days ago" | ✓ |
| Show "no recent fitness data" — skip Today section | Strict; refuse to render readiness | |
| Use last entry of any age (within long-term window) | Up to 42 days back; risks stale CTL | |

---

## RPE Data-Quality Threshold & Scope

### Lock the >30% threshold or tune it?

| Option | Description | Selected |
|--------|-------------|----------|
| Lock at >30% missing RPE | Matches ROADMAP success criterion verbatim | ✓ |
| Tighter — >20% missing | More aggressive nudging | |
| Looser — >50% missing | Quieter; warns only on heavy gaps | |

### Which activities count for the denominator?

| Option | Description | Selected |
|--------|-------------|----------|
| Climbing-relevant only — type==WeightTraining | Tied to v1 climbing-first scope | ✓ |
| All activities in window | Catches gaps in non-climbing efforts too | |
| All activities, separate climbing-vs-other counts | Two numbers; more tokens | |

### RPE window — same as the rest, or different?

| Option | Description | Selected |
|--------|-------------|----------|
| Use the 14-day window decided in Area 2 | One window query covers RPE coverage AND long-term trend's recent edge | ✓ |
| Use a 7-day window for RPE | Tighter; noisier on travel/rest weeks | |

### Small-sample suppression?

| Option | Description | Selected |
|--------|-------------|----------|
| Suppress warning, note "low activity volume" if <3 acts | Skip 30% test on tiny samples; cue user that signal is light | ✓ |
| Always run the threshold check | Apply 30% regardless of sample size | |
| Suppress silently — no note | Drop without comment | |

---

## Token Budget Enforcement & Empty-Data Handling

### How is the 400-600 token target verified?

| Option | Description | Selected |
|--------|-------------|----------|
| tiktoken cl100k_base — runtime + tested | Add tiktoken dep; unit test asserts sample lands in 400-600; tool itself does not block at runtime | ✓ |
| Rough char-count approximation | ~4 chars/token; no new dep; less accurate | |
| tiktoken at runtime + truncate if over | Defensive but adds branching and risks silently dropped sections | |

### What if data is empty or sparse?

| Option | Description | Selected |
|--------|-------------|----------|
| Degrade gracefully with named-section explanations | "No wellness in last 7 days" inline; tool always returns SOME report | ✓ |
| Error if today's CTL/ATL is missing | Hard-fail when readiness can't render | |
| Silently omit empty sections | Quiet output; user can't tell data is missing | |

### Module placement?

| Option | Description | Selected |
|--------|-------------|----------|
| New tools/status.py + utils/status.py | Climbing precedent — own concern, own files | ✓ |
| Add to tools/wellness.py | Wellness already pulls CTL/ATL but file is large | |
| Add to tools/activities.py | Activities owns icu_ctl/icu_atl but file is largest, explicitly avoid | |

### Tool params — what's the public signature?

| Option | Description | Selected |
|--------|-------------|----------|
| athlete_id + api_key, optional as_of_date | Default today; lets Claude ask "last Tuesday" | ✓ |
| athlete_id + api_key only — always today | Simplest; no time travel | |
| Full window override params | Maximum flexibility; surface wider than v1 needs | |

---

## Claude's Discretion

- Aggregation shape for the wellness-blend bullets (mean / latest / latest+delta) — planner picks what reads well in budget.
- Whether `format_*_section` helpers take dicts or typed kwargs.
- Whether tests use recorded JSON fixtures or hand-crafted dict literals.

## Deferred Ideas

- Optional window-override params — v2 if real use needs them.
- TSB band tuning (climbing-specific or conservative variants).
- Reading TSB from a future API field if Intervals.icu adds it.
- Cross-validation between wellness and per-activity CTL/ATL.
- Generic / non-climbing readiness reporting (covered by GEN-v2-01 in PROJECT.md).
