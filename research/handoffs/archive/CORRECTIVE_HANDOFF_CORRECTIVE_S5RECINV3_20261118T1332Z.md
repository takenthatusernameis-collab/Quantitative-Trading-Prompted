# Corrective Handoff — Session 5 Recovery Inv 3 (2026-11-18T13:32Z)

## Context
- Invocations 1 and 2 of the session-5 recovery correctly ran the pre-gate cheap path
  (`scripts/pre_gate_check.sh` → EXIT=0, STOP) and produced no durable changes. The clock
  gate is **2026-11-18T22:00:00Z (epoch 1795039200)**; at 13:32Z it is ~8.5h away, so the
  mutating extend MUST NOT run (NEXT_AGENT_TASK.md scope boundary #54). Per scope boundary
  #58 a redundant per-session re-verification note is not warranted either.
- To produce durable progress **without** violating the gate, this invocation made a
  materially different, behavior-preserving correction: removed two ruff-flagged dead/
  duplicate code defects (F601, F841) in two research scripts. This mirrors the accepted
  precedent of prior corrective cycles that fixed research-tooling defects without touching
  gates/thresholds/cost model/universe/clock-gate/data.

## What changed (exactly two deletions, behavior-preserving)
1. `research/eval_cryptofunding.py:1791` — removed the duplicate dict key
   `"fixed_coin_portfolio_accounting": fixed_coin_accounting,`. The identical key+value is
   already set at line 1777 in the same returned dict literal, so the dict content is
   unchanged (ruff F601 "dictionary key literal repeated").
2. `research/run_cycle19.py:975` — removed the dead local `dsr_actual = mult["dsr"]`
   (never read anywhere; ruff F841). Its informative comment
   (`# pre-registered and evaluated count both = 12`) was preserved by moving it above the
   live `dsr = mult["dsr"]` on line 974. The DSR itself is still computed (line 768),
   printed (790), stored (796) and surfaced in the report (lines 1241–1286) — no gate or
   decision wiring was touched.

Not touched (deliberately, to keep blast radius minimal): the separate F841
`symbol = base[:3]` at `research/eval_cryptofunding.py:1224` (not in the recommended removal
set). No thresholds / gates / cost model / universe / clock-gate logic / `data/raw` changed.

## Exact verification commands and observed outputs
- `ruff check research/eval_cryptofunding.py research/run_cycle19.py --select F601,F841`
  → before: 3 errors (symbol F841, F601 dup key, dsr_actual F841); after: **1 error**
  (only the intentionally-left `symbol` F841). F601 and `dsr_actual` F841 gone.
- `ruff check research/eval_cryptofunding.py research/run_cycle19.py` (total)
  → before: **36 errors**; after: **34 errors** (exactly the two removed; no new codes).
- `python -m py_compile research/eval_cryptofunding.py research/run_cycle19.py` → **COMPILE_OK**.
- `pytest -q tests/test_eval_cryptofunding.py tests/test_eval_cryptofunding_001.py`
  → **68 passed in 11.34s**, EXIT=0 (identical to the 68-passed pre-edit baseline).
- `pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py`
  → **74 passed in 8.59s**, EXIT=0.
- `ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py`
  → **All checks passed!**
- `git diff` → only the two intended deletions (eval_cryptofunding.py: 1 deletion;
  run_cycle19.py: 1 insertion [comment] + 1 deletion [dead var]).
- `git status --porcelain -- data/raw` → empty (clean).
- `GATE_EPOCH=1795039200 STATE_SHA256=05ca6c2f... bash scripts/pre_gate_check.sh`
  → **EXIT=0**: `PRE-GATE OK: now=1795008743 (13:32:23Z) < gate 1795039200 (22:00:00Z);
  T-30457s remaining; state sha256 matches; data/raw clean. STOP`.
- `sha256sum data/processed/paper_trading_state.yaml` → `05ca6c2f7ef25c00...` (unchanged).

## Durable progress
- Working tree now carries a real, verified, behavior-preserving code-quality fix to two
  research scripts (2 files, 1 insertion / 2 deletions). Controller checkpoints at the
  session boundary (no manual commit, per scope boundary #56).

## Unresolved blockers
- **Clock gate not reached.** The mutating extend (Step 2, `scripts/post_gate_orchestrator.sh`)
  is blocked until **2026-11-18T22:00:00Z**. This is the sole reason the trading state has
  not advanced; it is a hard safety boundary and must not be bypassed.
- Full ruff-clean of these two files (34 remaining pre-existing errors, mostly F401/F841/
  E402 in research code) is out of scope and was not attempted.

## Next distinct investigation (for the gate-active window / next bounded session)
- **Fold-12 artefact** documented in `research/reports/data_cost_inventory_002.md` §4.4:
  the point-in-time-complete subsample gives 41-fold mean OOS Sharpe **0.787522 (FAIL < 0.9)**,
  but with fold 12 removed, 40 folds give **1.352958**. The result depends on a single fold.
  A bounded next task: identify exactly which calendar period fold 12 covers, whether it
  coincides with a known data/regime artefact (e.g. a stale/duplicate bar, a symbol
  membership edge, or an extreme-volatility window), and record whether the dependence
  survives a placebo/parameter-perturbation check — WITHOUT changing the promotion gate or
  pre-registered thresholds. This is the highest-value research-integrity question currently
  open and does not require the trading extend.