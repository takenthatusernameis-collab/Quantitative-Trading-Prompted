# NEXT_AGENT_TASK.md

## Cycle 927 — COMPLETE (evidence below)

### What was done
Cycle 927 consolidated the same-session volatility estimate onto one shared implementation behind a default-off `lag_vol_estimate` switch in all seven research scripts that inlined it, and published the incumbent's corrected backtest as a new labelled successor reference.

**Implementation consolidation (verified, 16/16 per-script checks):**
- `research/run_cycle5.py` — `_apply_overlay` now calls `realized_vol_scale(..., lag_vol_estimate=False)`, default path bit-identical (max |diff| = 0.0)
- `research/run_cycle13.py`, `run_cycle15.py`, `run_cycle15_c4_corrected.py`, `run_cycle18.py`, `run_cycle19.py` — `_incumbent_overlay` routed through `realized_vol_scale`, default path bit-identical
- `research/run_cycle19.build_overlay_weights` — threads `lag_vol_estimate=False`, bit-identical
- `research/month_end_candidate_reaudit.py` — `overlay_weights` routed through `realized_vol_scale`, default path bit-identical
- **Zero** remaining inline same-session exposure estimates (`vol_target / realized_vol`) in any of the seven scripts
- Switch defaults off everywhere (`SimulationConfig()`, `from_yaml`, `PaperTradingConfig`); no config file mentions the switch

**Corrected successor record published (supersedes nothing):**
- New report: `research/reports/tsmomentum_vol_estimate_consolidation_001.md`
- New experiment record: `research/experiments/tsmomentum_vol_estimate_consolidation_001.md`
- Anchor reproduced: published 48-fold WF mean 0.947307, committed 450 sessions (max |diff| = 5.4e-20), published 2018-2026 baseline 1.4178
- Corrected path: canonical Sharpe 1.771084 -> 1.635705, trailing 63d -0.448918 -> -0.515807, PSR 0.695606 -> 0.623929, decision NO-GO on both paths
- Corrected 48-fold mean 1.318605 (artefact fold caveat: comparable statistic 1.346660 vs 1.431928, lower)
- Corrected path's own 2018-2026 backtest reference 1.335983 (vs unchanged 1.4178)
- Read-only: `data/` and `config/` byte-identical; no committed artifact modified

**Tests:** `tests/test_tsmomentum_vol_estimate_consolidation.py` — 24 passed.

**Incumbent unchanged:** Credible Candidate (published verdict), NO-GO promotion decision (unchanged).

### Next task (bounded)
Execute the corrected live paper-trading record start procedure specified in Cycle 927 section 4:
- Create a new config file (not editing committed configs) with `lag_vol_estimate: true`
- Start a new state file `data/processed/paper_trading_state_corrected_001.yaml` with re-initialised drift flags and gate table
- The `track_record_length` gate requires 126 sessions, so promotion evidence restarts from zero
- The corrected path's own backtest reference is 1.335983; the unchanged PSR reference 1.4178 is stricter
- No live trading, no fetcher call, no committed record modified, no config edit to committed files

This follows from the Cycle 927 evidence: the procedure was specified but not executed, and the next bounded step is to execute it so the corrected path has a live record to measure against.

## Validation commands
```bash
python research/tsmomentum_vol_estimate_consolidation.py --no-report
python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py
python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py
git status --porcelain data/ config/
```

## Scope boundaries
- `data/` and `config/` read-only except the new state file and new config file for the corrected record
- No committed record, committed config, or committed paper-trading state may be modified
- No live trading, no fetcher call, no new dependency
- The committed record stays published and NO-GO; the corrected record starts fresh (126 sessions)
