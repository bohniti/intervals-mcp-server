# Deferred items - Phase 02

Out-of-scope discoveries during execution. Not fixed here.


## From plan 02-04 (2026-04-25)

- Pre-existing mypy errors in `src/intervals_mcp_server/utils/formatting.py`:
  - `formatting.py:28: Argument 1 to "add" of "set" has incompatible type "object"; expected "str"`
  - `formatting.py:358: "dict[str, Any]" has no attribute "accessed"`
  Pre-date Plan 02-04 changes; both `git stash` confirm pre-existing. Out of
  scope per Plan 02-04. Suggested fix: type-narrow the dict access and the set
  membership check; possibly add a TypedDict or per-field cast. File not
  touched by Plan 02-04, so not within deviation Rule 1 scope.
