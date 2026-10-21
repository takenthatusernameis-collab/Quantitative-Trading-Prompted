# NEXT_AGENT_TASK.md

## Cycle 920 — Evaluate SMA-175 candidate against full promotion gate suite

### Context
Cycle 918 added `research/tsmomentum_sma175_candidate_eval.py` — an independent walk-forward evaluation of a TSMomentum candidate with SMA-175 trend filter (vs incumbent SMA-200) over 48 folds, producing WF mean OOS Sharpe 1.5400 (gate 1 >= 0.9 passes). However, the candidate has not been evaluated against the full promotion gate suite: full_period_sharpe, rolling_63d_sharpe, max_drawdown, rolling_63d_max_dd, psr, regime_flips, track_record_length. The incumbent (`simulation_candidate_001`) is NO-GO on these gates; `csmomentum_001` and `sectorrotation_001` are Rejected/Failed. A complete gate verdict for the SMA-175 variant is needed to label it (credible candidate / rejected / failed).

### Objective
Run the SMA-175 candidate through the repository's full promotion gate evaluation and publish a complete gate table + decision. Read-only: no network, no writes under data/ or config/, no changes to run_cycle6.py or any committed artifact. Reuse existing infrastructure (`src/backtest/engine.py:run_backtest`, `src/evaluation/walkforward.py`, `config/promotion_gates.yaml`) where possible.

### Acceptance criteria
1. A new read-only tool evaluates the SMA-175 candidate (SMA window 175, otherwise identical to `run_cycle6.py` config) and prints a full gate table: full_period_sharpe, rolling_63d_sharpe, max_drawdown, rolling_63d_max_dd, psr, regime_flips, track_record_length, plus the decision mapping (GO / NO-GO / INCONCLUSIVE).
2. Tool prints `OVERALL: PASS` only if all internal structural checks pass; fails closed otherwise.
3. `git status --porcelain data/ config/` -> empty (nothing written under data/ or config/).
4. `git diff --stat -- research/run_cycle6.py` -> empty (incumbent baseline not mutated).
5. Committed artifacts under `research/experiments/` and `research/reports/` byte-identical before and after (except the new report written by this tool).
6. No new dependencies; no network access.

### Scope boundaries
- Do not change any source, config, data, or committed artifact.
- Do not add dependencies, services, or infrastructure.
- Research/backtesting only; no live trading, no secrets, no credentials.
- The incumbent's published protocol, gates, and record are unchanged; this is an independent evaluation of the SMA-175 variant only.

### Validation commands
```bash
python research/tsmomentum_sma175_promotion_gate_eval.py
git status --porcelain data/ config/
git diff --stat -- research/run_cycle6.py
```

### Evidence artifacts
- New tool: `research/tsmomentum_sma175_promotion_gate_eval.py`
- New report: `research/reports/tsmomentum_sma175_promotion_gate_eval_001.md`
- New experiment record: `research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md`
- Full gate table values and decision
- `git status` / `git diff` output showing data/, config/, run_cycle6.py unchanged

### Handoff (for the cycle after)
- Changed: NEXT_AGENT_TASK.md prepared (Cycle 920).
- Verified (prior): Cycle 918 SMA-175 walk-forward: 48 folds, mean Sharpe 1.5400, OVERALL: PASS; Cycle 919 full suite: 413 passed, exit 0; data/config/run_cycle6.py immutable.
- Unresolved: SMA-175 candidate's full promotion gate verdict (max DD, PSR, rolling 63d Sharpe, trade count not yet evaluated).
- Failed approaches: none.
- Next task: run Cycle 920 tool, confirm gate verdict, then advance based on the decision.