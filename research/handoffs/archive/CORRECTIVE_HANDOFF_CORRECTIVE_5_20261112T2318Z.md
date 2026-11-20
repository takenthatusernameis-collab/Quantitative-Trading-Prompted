# CORRECTIVE_HANDOFF — Corrective invocation 5 (2026-11-12T23:18Z)

## Why this invocation differs from prior failed ones
- Prior invocation (375) exited status 1 with a **provider/infrastructure** error, not a
  project defect: `/home/runner/work/_temp/kilo-session-3-recovery-375.log` shows only
  `Error: Sign up for free to continue and explore 500 other models…`. That is a free-model
  quota wall, not a repo failure.
- Prior corrective invocations 2/3/4 only wrote/committed handoff prose and re-verified an
  already-clean baseline. This invocation instead **found and fixed a real defect** in the
  durable handoff generator that the current `NEXT_AGENT_TASK.md` explicitly relies on
  (`prefer scripts/post_gate_orchestrator.sh because it writes a durable, in-repo handoff`).

## Defect found (evidence)
`scripts/post_gate_orchestrator.sh` hardcoded `2026-11-12` labels in the generated handoff
regardless of the `GATE_EPOCH` override. For the sanctioned 2026-11-13 gate
(`GATE_EPOCH=1794607200`) it would emit a factually wrong artifact. Demonstrated:
```
$ GATE_EPOCH=1794607200 … echo "Gate epoch: $GATE_EPOCH (2026-11-12T22:00:00Z)"
Gate epoch: 1794607200 (2026-11-12T22:00:00Z)     # WRONG label
$ date -u -d @1794607200 +%FT%TZ
2026-11-13T22:00:00Z                              # true value
```
AGENTS.md requires accurate date ranges in evidence artifacts, and NEXT_AGENT_TASK depends on
this script for the in-repo handoff, so a wrong date label would corrupt the next cycle's
evidence. This is a documentation-output defect, not a gate/threshold/cost/universe change.

## Change made (smallest sufficient, in scope)
`scripts/post_gate_orchestrator.sh`:
- Added `GATE_HUMAN="$(date -u -d "@$GATE_EPOCH" +%FT%TZ)"` (derived from `GATE_EPOCH`).
- Handoff title now `cycle for gate $GATE_HUMAN`; gate-epoch line now `$GATE_EPOCH ($GATE_HUMAN)`.

Untouched: gate decision logic (`if (( now_epoch < GATE_EPOCH ))`), thresholds, cost model,
universe, `data/raw/`, `data/`, `config/`. No gate parameter default changed.

## Verification (exact commands & observed outputs)
1. `bash -n scripts/post_gate_orchestrator.sh` → `SYNTAX_OK`
2. Derived-label check:
   - default `GATE_EPOCH=1794520800` → `GATE_HUMAN=2026-11-12T22:00:00Z`
   - override `GATE_EPOCH=1794607200` → `GATE_HUMAN=2026-11-13T22:00:00Z`
3. End-to-end real script, read-only, 2026-11-13 gate:
   `GATE_EPOCH=1794607200 HANDOFF=/tmp/handoff_e2e_20261113.md bash scripts/post_gate_orchestrator.sh --force --read-only`
   - cmd5 6-module pytest: `68 passed in 27.66s`
   - cmd7a inventory: `35 raw files, 180279 rows, 0 missing prices, 0 duplicate timestamps`;
     `8/8 digests match`; shortlist TSMOM incumbent 31/35
   - cmd7b: `DECISION|NO-GO|incumbent tsmomentum_spytrend_001 unchanged`; `OVERALL: PASS`
   - cmd7c pytest: `41 passed in 52.55s`
   - cmd8 ruff: `All checks passed!`
   - Generated handoff now: `cycle for gate 2026-11-13T22:00:00Z` and
     `Gate epoch: 1794607200 (2026-11-13T22:00:00Z)` — correct.
4. Repo integrity after run: `git status --porcelain` shows only
   ` M scripts/post_gate_orchestrator.sh` and the pre-existing untracked inv4 handoff.
   `data/processed/paper_trading_state.yaml` SHA256 unchanged
   `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a`
   (`last_run=2026-11-12`, `nav=133039.92504076837`, `runs=468`). cmd7 reports regenerated
   byte-identically (no diff).

## Unresolved blockers
- **Primary (time gate, not a defect):** the 2026-11-13 extension gate
  (epoch 1794607200 = 2026-11-13T22:00:00Z) is not yet released (~22.7h out at 2026-11-12T23:15Z).
  Per scope: do NOT run the mutating extend (cmd2) before the gate; do NOT re-extend 2026-11-12.
- **Secondary (minor robustness, not fixed — out of scope):** `--force` is only honored as the
  first CLI arg (`[[ "${1:-}" != "--force" ]]`); `--read-only --force` does not bypass the clock
  gate. Does not affect the sanctioned no-flag path. Flag as an optional next-task item.

## Next distinct action (evidence-supported)
- At/after 2026-11-13T22:00:00Z run:
  `GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh`
  (fallback: manual cmds 1–8 from `NEXT_AGENT_TASK.md`). Extend by ≤1 session to 2026-11-13 only
  if a completed bar exists; else `sessions_extended==0`, 0 writes.
- Optional distinct follow-up (separate bounded task): make `--force` position-independent in the
  orchestrator arg loop, with a regression check. Do not bundle with the gate run.

## Safety
No alpha/promotion claims. No live trading, secrets, credentials, or account access. Research
pre-registrations, promotion gates, security controls, workflow boundaries, and user data
preserved. Gate/threshold/cost/universe logic unchanged. No commit made.