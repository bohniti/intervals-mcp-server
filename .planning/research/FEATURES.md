# Feature Research

**Domain:** Climbing training session logging + load management, integrated into Intervals.icu via MCP
**Researched:** 2026-04-24
**Confidence:** MEDIUM (domain knowledge from climbing training literature; dedicated climbing apps not directly inspectable due to tooling restrictions — see Sources)

---

## Domain Context

This MCP extension targets a single climber who already uses Intervals.icu as their training hub. The competitive set is not head-to-head with Lattice, Crimpd, or 8a.nu — it is the friction-free alternative to opening a second app after a session. The value is: stay in Claude, say what you did, have it land correctly in Intervals.icu. Everything below is evaluated through that lens.

---

## What Climbers Actually Capture Per Session

Research across climbing training literature (Lattice Training methodology, Crimpd app, Eva Lopez's work, Ned Feehally / Beastmaking guidance, and community logbook conventions) surfaces two clear tiers.

### Minimum Useful Set (what every serious logger captures)

1. **Discipline** — bouldering / sport lead / top-rope / system board / fingerboard / hangboard / antagonist. Without this, the log is uninterpretable.
2. **Venue type** — gym vs outdoor. Affects reference grade validity and skin conditions.
3. **Session duration** — total time at wall, not just climbing time.
4. **Sends / attempts at grade** — the core volume signal. Even a rough count (e.g., "5 problems around 7a, one 7b project, 3 attempts") is sufficient.
5. **Hardest grade touched** — quick proxy for intensity ceiling.
6. **RPE (1–10)** — perceived exertion for the whole session, the single best scalar for climbing load.
7. **Session focus / intent** — power / endurance / technique / projecting / volume / antagonist. Needed to interpret load in context.
8. **Notes / quality comment** — free text. "Skin wrecked after 3 hours" is as important as any number.

### Power-User Set (what serious loggers add)

9. **Per-route / per-problem breakdown** — grade, style (crimpy/slopey/pinchy/dynamic), send/attempt, attempt number on project.
10. **Finger condition / skin condition** — 1–5 scale or text. Frequent limiter that affects training decisions more than any fitness metric.
11. **Training stimulus intent** — energy system targeted (ATP-PCr / glycolytic / aerobic).
12. **Quality of movement rating** — separate from RPE; "body felt strong but movement was sloppy" is a real signal.
13. **Rest intervals / density** — matters for fingerboard/hangboard sessions especially.
14. **Partner / team session vs solo** — social climbing changes effort selection.
15. **Route style tags** — roof / slab / vertical / overhang; crack / face; power-endurance emphasis.
16. **Media / beta notes** — photos, video links, sequence notes per problem.

### Garmin-Synced Climbing Activity — What It Provides vs What's Missing

A Garmin device recording a "Climbing" activity typically provides:
- Start time, elapsed time, active time
- Heart rate (avg, max, min) — often unreliable on steep terrain due to arm position
- Calories (estimated)
- GPS track (outdoors only)
- Lap splits if manually lapped

**Systematically absent from Garmin:**
- Discipline / venue type
- Any grade information
- Attempt / send counts
- Session focus
- RPE (Garmin has an "RPE" prompt on some devices post-activity, but it does not reliably sync to Intervals.icu as `icu_rpe`)
- Skin / finger condition
- Route-level breakdown

This means a Garmin-synced climbing activity is essentially an HR blob with a timestamp. The enrichment job is to overlay all the meaningful climbing context on top of it. The activity already exists; the tool needs to UPDATE it with custom fields + RPE, not create it.

---

## Climbing-Specific Load Metrics

### The Core Problem

Climbing has no power meter equivalent. TSS (Training Stress Score) in cycling/running requires a continuous objective intensity signal. Climbing load is inherently intermittent, skill-dependent, and grade-relative to the individual — a 7b for one climber is warmup, for another it is maximal.

### What Practitioners Actually Use (evidence-based)

**rpeTSS (session RPE × duration):** The most widely recommended approach for climbing in the absence of power meters. Intervals.icu natively computes this from `icu_rpe` + session duration. Formula: `rpeTSS = (duration_hours × RPE × 10) × (RPE / max_RPE)`. This is the primary load unit this project should feed.

**Volume at grade (sends × grade weight):** Lattice Training and several coaching frameworks assign a numeric "difficulty score" to each grade bracket and multiply by send count to get session volume. Example weight table (Font bouldering):
- 5c–6a: weight 1
- 6b–6c: weight 2
- 7a–7b: weight 3
- 7c+: weight 5+
This produces a session "volume score" that is more sensitive than pure attempt count and accounts for grade ceiling work.

**Attempts / touches as fatigue proxy:** The number of total contacts (attempts on hard problems especially) is the primary finger-tendon loading signal. High attempt count at high grade = high connective tissue stress. This is a better injury-risk signal than RPE alone. Crimpd tracks "ascents" and "attempts" separately for this reason.

**Pyramid completeness:** Coaches use a grade pyramid concept — you should have a wide base of sends below your project grade and progressively fewer at the top. A "pointy" pyramid (few sub-max sends, many max-grade attempts) indicates volume deficit. This is a derived metric from the grade log, not directly captured — but the raw data (sends per grade band) is what enables it.

**CTL/ATL/TSB on rpeTSS:** Intervals.icu already computes chronic training load (CTL), acute training load (ATL), and training stress balance (TSB) from rpeTSS. This is the primary readiness signal the status tool should surface. CTL ≈ fitness, ATL ≈ fatigue, TSB = CTL − ATL ≈ form/readiness.

**Weekly volume caps:** Coaches (Lattice, Progression, 8a Training) typically prescribe climbing training in 3–5 session/week structures with 10–20% load progression caps per week. These are population-level guardrails, not personalized, but inform the "weekly load" section of the status report.

### What This Project Should NOT Try to Compute

- A proprietary "climbing TSS" formula — inventing one creates confusion vs Intervals.icu's rpeTSS; stick with rpeTSS
- Energy system modeling from HR alone — climbing HR data is too noisy for reliable aerobic/anaerobic split
- Grade-weighted volume as an automated metric — the raw data (sends per grade) should be stored; derived math can be done by Claude on top of it rather than baked into a tool

---

## How Coaches Read Readiness

Based on published coaching frameworks (Lattice, Udo Neumann, Steve Bechtel, Atomik training philosophy):

### Inputs Weighted by Coaches

1. **TSB (CTL − ATL)** — primary quantitative signal. Negative TSB = accumulated fatigue. TSB near zero or slightly positive = peak form. Very positive TSB (detrained) = fitness loss. Typical climbing training TSB range: −20 to +10.

2. **HRV trend** — morning HRV relative to personal baseline. A drop of >10–15% from 7-day rolling average is a reliable recovery flag. Single-day HRV is noisy; trend matters. Coaches look at 3–7 day directional trends, not individual values.

3. **Subjective fatigue + soreness** — Intervals.icu has `fatigue` and `soreness` (1–10). Both are self-reported and highly predictive of session quality. Coaches weight these heavily because finger tendons and skin don't show up in any biometric.

4. **Sleep quantity + quality** — `sleepSecs` / `sleepHours` + `sleepQuality`. Sleep <7h or poor quality flags recovery deficit. Coaches treat consecutive nights of poor sleep as a hard brake on intensity sessions.

5. **Finger condition / skin** — no standard biometric for this; it's subjective. A finger tweak or split skin is a categorical blocker for certain session types regardless of what CTL/ATL says. This is the most climbing-specific readiness input and the hardest to capture systematically.

6. **RHR (resting heart rate)** — elevated RHR vs personal baseline (>5–7 bpm above 7-day average) signals illness or deep fatigue. Less sensitive than HRV for athletic recovery but easier to capture reliably.

7. **Days since last rest day** — simple consecutive-training-day count. Most coaches cap consecutive climbing days at 2 (for higher-intensity) or 3 (for volume/mileage work). Beyond that, injury risk rises disproportionately.

### What Coaches DON'T Rely On

- Single-session HR data for climbing (too noisy, position-dependent)
- Body weight fluctuations day-to-day (hydration noise)
- Grade comparisons across gyms (conditions vary too much)

---

## "Status Report" Format — What Climbers Actually Want

Based on community usage patterns and the Intervals.icu native "Form" concept:

### The Three-Part Structure

1. **Today's readiness** — a single verdict: "train hard / train easy / rest." Optionally a traffic-light color. Backed by 2–3 data points explaining the verdict.
2. **Weekly load review** — what was done this week vs recent weeks. Load trend (building / maintaining / recovering). Days climbed, total load, sessions by discipline.
3. **Long-term trend** — CTL direction (building fitness?), TSB history, any warning signs (ATL spikes, consecutive negative TSB).

### Format Preferences (from climbing training community norms)

- **Prose verdict first, numbers second.** "You're fresh — TSB is +5 after a full rest day. HRV is on-trend. Good day for a hard bouldering session." Then: "CTL 42, ATL 38, TSB +4. HRV 62 (baseline 58). Sleep 7.5h."
- **Traffic-light is optional** but appreciated for quick scanning: Green / Amber / Red.
- **Not a wall of numbers.** Climbers switch off if readiness outputs look like a training peaks data dump.
- **Specific about what type of session** — don't just say "train hard," say "good conditions for high-intensity bouldering or limit-grade sport. Avoid fingerboard heavy days if skin is worn."

### What the LLM (Claude) Does vs What the Tool Does

The **tool** collects and formats the raw data: CTL, ATL, TSB, recent wellness entries, recent activity summaries.

The **LLM** synthesizes the verdict: "Given TSB +4, HRV trend stable, and sleep 7.5h, here's what I'd suggest..."

The tool should NOT try to encode the coaching logic. The tool returns structured data; Claude interprets it. This is the key differentiator — the LLM provides the contextual reasoning that a static app cannot.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features without which the tool has no reason to exist as a "climbing training loop."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Write RPE to `icu_rpe` on existing activity | Core load signal; without this, Intervals.icu cannot compute rpeTSS for climbing | LOW | Native Intervals.icu field; PUT to `/athlete/{id}/activities/{id}` with `icu_rpe` payload |
| Write discipline (bouldering / sport / etc.) to activity | Without discipline, all sessions are indistinguishable blobs | LOW | Requires pre-defined custom field in Intervals.icu account (user prerequisite) |
| Write session focus (power / endurance / technique / projecting / volume) | Needed to interpret load in context of intent | LOW | Custom field; enum-style (5–6 values); validate against allowed set |
| Write grade-sent + grade-attempted (Font / French sport) | Core volume and intensity data; makes grade log queryable | MEDIUM | Custom field; accept structured list or highest-grade summary; Font + French sport only in v1 |
| Create climbing activity from scratch (no watch) | Timo logs manually; this is the primary creation path | MEDIUM | POST to `/athlete/{id}/activities`; must set `type`, `startTime`, `duration`, plus custom fields in same call or follow-up PATCH |
| Enrich existing Garmin-synced activity | Garmin provides the time/HR shell; user adds the climbing context | MEDIUM | GET activity id → PUT custom fields + RPE; must handle "activity already exists" gracefully |
| Mark planned calendar event as done by creating linked activity | Closes the plan→actual loop Intervals.icu is designed for | MEDIUM | POST activity with matching date + type; Intervals.icu auto-matches to event; no event mutation needed |
| Write wellness entries conversationally (sleep, soreness, fatigue, HRV, RHR) | Wellness data feeds readiness; tool must accept it naturally | MEDIUM | PUT to `/athlete/{id}/wellness/{date}`; existing read tool does not write; merge with existing entry rather than overwrite |
| Status report: CTL/ATL/TSB + recent wellness + load trend in one call | The "how should I train today?" answer; single LLM prompt should trigger one tool call that returns everything needed | HIGH | Compose: fetch wellness (last 14d), fetch activities (last 28d), return structured data for LLM to interpret |

### Differentiators (Competitive Advantage)

Features that make this tool worth using instead of (or in addition to) a dedicated app.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Conversational session capture — Claude gathers fields, one tool call commits | No form to fill out; natural language → structured data. Crimpd and Lattice require manual form entry. This is the key UX differentiator | LOW (tool side) / HIGH (prompt engineering) | The tool parameters must be maximally optional with sensible defaults so Claude can call with whatever the user mentioned |
| Readiness interpretation by LLM rather than algorithmic score | Claude can weight subjective climbing-specific signals (skin condition, consecutive days, specific fatigue type) that a rule-based app cannot. Lattice's readiness output is a fixed algorithm; Claude can reason about context | ZERO (no tool work — Claude does this) | The status tool just returns clean data; Claude's reasoning IS the differentiator |
| Venue context (gym vs outdoor, specific wall) | Lattice/Crimpd track this; many climbers want to split gym load from outdoor; useful for grade calibration | LOW | Single custom field; free-text or enum |
| Finger condition / skin as a first-class field | Biggest climbing-specific readiness signal; almost universally ignored by fitness trackers but critical for injury prevention | LOW (capture) / MEDIUM (surface in status report) | Custom field (1–5 scale or text); status report tool should explicitly surface this alongside HRV/sleep |
| Grade-aware volume trend (sends per grade band over time) | Enables pyramid analysis; no dedicated app does this integrated with a training load platform | HIGH | Requires querying past activities' custom fields and aggregating; medium complexity for the status tool variant; HIGH if we build a dedicated pyramid tool |
| Single-tool status report spanning load + wellness + recent sessions | No siloing between "training" and "health." Intervals.icu shows this but requires navigating multiple screens; one Claude query delivers it as prose | HIGH | Must fetch from three endpoints (activities, wellness, athlete fitness) and synthesize into coherent output for LLM |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Per-route / per-problem logging as structured data | Power users want a full tick list | Requires a separate data model (list of attempts per problem); cannot cleanly fit in flat Intervals.icu custom fields; becomes a mini database; out of scope for v1 | Store as free-text session notes field; per-problem logging is a v2+ dedicated feature with its own data model |
| Grade conversion between Font / V-scale / YDS | Users sometimes ask "what's 7a in V?" | Creates false precision; Font and V-scale don't map cleanly; invites misuse of conversion for grade comparisons across systems | Document the limitation; support Font + French sport only; conversions are Claude's job from training knowledge |
| Automated training plan generation or prescription | Coaches know readiness → plan suggestions are natural | Requires athlete model, progression logic, and injury risk modeling — scope is 10x the current milestone; wrong outputs are actively harmful | v1 status tool returns state; Claude (not the tool) does the reasoning; formal prescription is a future milestone |
| Storing climbing data locally in a side file | Avoids Intervals.icu prerequisites | Violates single-source-of-truth constraint; creates sync problems; makes data invisible to Intervals.icu analytics | All structured data goes to Intervals.icu custom fields; document the setup prerequisite clearly |
| Fingerboard / hangboard protocol logging as dedicated tool | Fingerboard is common training mode | Adds a third activity creation path (scratch / Garmin-sync / hangboard) for v1; hangboard sessions have their own protocol structure (holds, edge size, hang/rest times) | v1: hangboard as "bouldering + session_focus=fingerboard" with notes; v2: dedicated hangboard tool if usage warrants it |
| Multi-session day (AM + PM sessions) automatic splitting | Garmin sometimes creates two activities | Edge case; complex to handle correctly; Intervals.icu handles multi-activity days natively | Let Intervals.icu handle day aggregation; each session is one tool call regardless |
| Image / video upload for beta | Climbers photo-document problems | Not an Intervals.icu capability; no API endpoint exists; requires a completely different storage layer | Free-text notes field referencing external media links |
| "Best sessions" / PR tracking | Climbers want to know their hardest send ever | Requires querying all historical activities' custom fields — expensive and slow; no Intervals.icu index on custom fields | Ask Claude to query recent sessions; historical PR tracking is a v2 feature needing efficient indexing |

---

## Feature Dependencies

```
[Write wellness entries]
    └──required by──> [Status report]
                          └──enhanced by──> [Grade-aware volume trend]

[Write RPE to activity]
    └──enables──> [rpeTSS computation in Intervals.icu]
                      └──required by──> [CTL/ATL/TSB in status report]

[Create climbing activity from scratch]
    └──shares implementation with──> [Mark planned event as done]
                                         (both POST a new activity; event version uses matching date/type)

[Enrich Garmin-synced activity]
    └──shares implementation with──> [Write RPE to activity]
                                         (both are PUT/PATCH on existing activity)

[Discipline field]
    └──required by──> [Session focus field]
    └──required by──> [Grade fields]
    (without discipline, grade and focus are ambiguous)

[Finger condition field capture]
    └──enhances──> [Status report readiness signal]
    └──enhances──> [Wellness write tool]
    (can live in wellness or activity custom field — decide at implementation)
```

### Dependency Notes

- **Status report requires wellness write to exist:** The status report reads wellness; for the loop to be closed, the user must be able to write wellness in the same workflow. If wellness write is deferred, the status report still works with read-only wellness data — it just won't include freshly logged morning data.
- **rpeTSS chain:** `icu_rpe` write → Intervals.icu computes rpeTSS → rpeTSS feeds CTL/ATL → CTL/ATL appear in status report. Without RPE writes, the load metrics in the status report are stale or absent for climbing activities.
- **Custom fields are a prerequisite gate:** Writing discipline, grade, or session_focus requires those fields to exist in the athlete's Intervals.icu account. This is a user prerequisite (documented), not a code dependency — but it affects which features are usable day one.
- **Create from scratch and enrich Garmin share the same field set:** The parameters for climbing context (discipline, grades, session focus, RPE, notes) are identical regardless of whether we're creating a new activity or enriching an existing one. The tool interface should be consistent.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what closes the training loop for Timo.

- [ ] **Write RPE to existing activity** — the single most impactful change; enables rpeTSS; no custom fields needed
- [ ] **Enrich existing activity with discipline + session_focus + grade summary** — turns a Garmin blob into a meaningful climbing record
- [ ] **Create climbing activity from scratch** — covers manual sessions (majority of Timo's sessions)
- [ ] **Mark planned event as done** — closes the calendar loop; relies on Intervals.icu auto-matching
- [ ] **Write wellness entries** — sleep, fatigue, soreness, HRV, RHR; minimal field set that feeds readiness
- [ ] **Status report** — CTL/ATL/TSB + last 7 days wellness + recent session summary; returns structured data for Claude to interpret

### Add After Validation (v1.x)

- [ ] **Finger condition / skin as explicit field** — add to wellness write or activity custom field based on v1 usage patterns; trigger: user requests it after v1 ships
- [ ] **Venue context (gym vs outdoor)** — low effort add; trigger: user asks about gym vs outdoor split in status report
- [ ] **Grade-band volume aggregation in status report** — add grade pyramid summary to status output; trigger: status report proves useful and user wants more climbing specificity

### Future Consideration (v2+)

- [ ] **Per-problem / per-route structured log** — needs its own data model; defer until v1 patterns settle
- [ ] **Fingerboard protocol tool** — dedicated hangboard session logger; defer until hangboard usage patterns are understood
- [ ] **Historical PR tracking** — requires efficient querying of historical custom fields; performance work needed
- [ ] **Generic manual activity creation** (non-climbing) — out of scope per PROJECT.md; v2 only

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Write RPE to activity | HIGH | LOW | P1 |
| Create climbing activity from scratch | HIGH | MEDIUM | P1 |
| Enrich Garmin-synced activity with climbing context | HIGH | MEDIUM | P1 |
| Mark planned event as done | HIGH | MEDIUM | P1 |
| Write wellness entries | HIGH | MEDIUM | P1 |
| Status report (CTL/ATL/TSB + wellness + sessions) | HIGH | HIGH | P1 |
| Discipline field (bouldering/sport/etc.) | HIGH | LOW | P1 — prerequisite: user must define custom field |
| Session focus field | MEDIUM | LOW | P1 — same prerequisite |
| Grade summary field (Font + French) | HIGH | MEDIUM | P1 — prerequisite |
| Venue context (gym vs outdoor) | MEDIUM | LOW | P2 |
| Finger condition / skin field | HIGH | LOW | P2 |
| Grade-band volume trend in status report | MEDIUM | MEDIUM | P2 |
| Per-problem structured log | HIGH | HIGH | P3 |
| Fingerboard protocol tool | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 milestone — without it the training loop is not closed
- P2: Should have, add after v1 validation
- P3: Nice to have, future milestone

---

## Competitor Feature Analysis

| Feature | Crimpd | Lattice | 8a.nu / Kaya | This MCP |
|---------|--------|---------|--------------|----------|
| Session RPE | Yes (1–10) | Yes | No (8a) / Yes (Kaya) | Yes — native `icu_rpe` |
| Discipline tagging | Yes | Yes | Partial | Yes — custom field |
| Grade logging per route | Yes (full tick list) | Yes | Yes (8a core feature) | v1: summary only; v2: per-route |
| Grade system support | Font, V-scale, YDS | Font, V-scale | Multiple | Font + French sport (v1) |
| Volume at grade aggregation | Yes (Crimpd) | Yes (Lattice AI) | No | Derived by Claude from stored data |
| Session focus / intent | Yes (Crimpd) | Yes | No | Yes — custom field |
| Finger condition tracking | Yes (Crimpd) | Yes (Lattice assessment) | No | v1.x wellness field |
| CTL/ATL/TSB load model | No | Lattice Fingerboard Score (different) | No | Yes — via Intervals.icu rpeTSS |
| HRV integration | No (most) | No | No | Yes — via Intervals.icu wellness |
| Sleep data integration | No | No | No | Yes — via Intervals.icu wellness |
| Readiness synthesis | Algorithm-based | Algorithm-based | No | LLM reasoning (Claude) — key differentiator |
| Calendar / planning integration | Crimpd has training plans | Lattice coaching | No | Yes — native Intervals.icu events |
| Conversational entry | No | No | No | Yes — via Claude |
| No additional app required | No | No | No | Yes — stays in Claude + Intervals.icu |

---

## Climbing-Load Math Reference

These are the grounded formulas/concepts the implementation should be aware of:

**rpeTSS (Intervals.icu native):**
`rpeTSS ≈ duration_hours × RPE × 10 × (RPE / 10)`
At RPE 6 for 2 hours: `2 × 6 × 10 × 0.6 = 72 TSS`
At RPE 9 for 1.5 hours: `1.5 × 9 × 10 × 0.9 = 121.5 TSS`
This is what feeds CTL/ATL/TSB. Getting RPE right is more important than any custom field.

**CTL (Chronic Training Load) = Fitness:**
Exponential moving average of daily TSS over ~42 days. A stable CTL of 40–60 TSS/day is typical for a dedicated recreational climber training 3–4x/week.

**ATL (Acute Training Load) = Fatigue:**
Exponential moving average of daily TSS over ~7 days. Spikes above CTL = accumulated fatigue.

**TSB (Training Stress Balance) = Form:**
`TSB = CTL − ATL`
- TSB < −20: Heavy accumulated fatigue; reduce load
- TSB −20 to −5: Normal training block; hard sessions OK
- TSB −5 to +5: Fresh; good for hard sessions
- TSB > +10: Detrained; fitness is being lost

**Grade Difficulty Weighting (Font bouldering, for volume scoring):**
This is not standardized — different coaches use different tables. A pragmatic minimal table:
- ≤6a: weight 1 (warmup territory)
- 6b–6c: weight 2
- 7a–7b: weight 3
- 7c: weight 4
- 8a+: weight 5
Multiply weight by sends to get session volume score. Store raw sends-per-grade; let Claude compute volume scores with whatever weighting makes sense in context.

---

## Sources

**Confidence notes:** Training data reflects literature through August 2025. Dedicated app research (Crimpd, Lattice) was not directly confirmable via live sources due to tooling restrictions during this research session. Competitor feature table is based on training knowledge and should be validated against current app state before feature decisions are finalized.

- Lattice Training methodology: latticetraining.com (training knowledge; not fetched live)
- Crimpd app feature set: crimpd.com (training knowledge; not fetched live)
- Udo Neumann climbing training principles — periodization and load management literature
- Steve Bechtel "Logical Progression" — climbing periodization book (training load chapter)
- Eva Lopez fingerboard and strength-endurance research — finger tendon loading emphasis
- Intervals.icu rpeTSS documentation — native field behavior and CTL/ATL/TSB math
- 8a.nu logbook conventions — grade logging norms (training knowledge)
- Community climbing training forums (Reddit r/climbharder, TheCrag, UKClimbing) — session logging conventions

---

*Feature research for: Intervals.icu MCP — Climbing Training Loop Extension*
*Researched: 2026-04-24*
