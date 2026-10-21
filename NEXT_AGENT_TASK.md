# NEXT_AGENT_TASK.md

## Cycle 927 — COMPLETE (evidence below)

### What was done
Cycle 927 consolidated the same-session volatility estimate onto one shared implementation behind a default-off `lag_vol_estimate` switch in all seven research scripts that inlined it, and published the incumbent's corrected backtest as a new labelled successor reference.

**Implementation consolidation (verified, 16/16 per-script checks):**
- `research/run_cycle5.py` — `_apply_overlay` now calls `realized_vol_scale(..., lag_vol_estimate=False)`, default path bit-identical (max |diff| = 0.0)
- `research/run_cycle13.py`, `run_cycle15.py`, `run_cycle15_c4_corrected.py`, `run_cycle18.py`, `run_cycle19.py` — `_incumbent_overlay` routed through `realized_vol_scale`, default path bit-identical
- `research/run_cycle19.build_overlay_weights` — threads `lag_vol_estimate=False`, bit-identical
- `research/month_end_candidate_reaudit.py` — `overlay_weights` routed through `realized_vol_scale`, default path bit-identical
- **Zero** remaining inline same-session exposure estimates in any of the seven scripts
- Switch defaults off everywhere (`SimulationConfig()`, `from_yaml`, `PaperTradingConfig`)

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

## Cycle 928 — COMPLETE (evidence below)

### What was done
Corrected live paper-trading record start procedure executed:
- New config `config/simulation_candidate_001_corrected.yaml` with `lag_vol_estimate: true` (byte-identical to committed `config/simulation_candidate_001.yaml` except the switch; does not edit any committed config)
- New state file `data/processed/paper_trading_state_corrected_001.yaml` with re-initialised drift flags and gate table (empty positions, null last_run_date, zero PnL)
- No live trading, no fetcher call, no committed record modified, no committed config edited
- `track_record_length` gate requires 126 sessions; promotion evidence restarts from zero on the corrected record

### Check fix (cycle 0047/0048/0049) — COMPLETE
The `no_config_file_sets_the_switch` check deterministically failed once `config/simulation_candidate_001_corrected.yaml` existed (it legitimately sets `lag_vol_estimate: true`). Fixed in all 4 mirrored sites:
- `research/tsmomentum_vol_estimate_consolidation.py` — explicit allowlist for `_corrected` config + positive invariant over record-feeding configs (`simulation_candidate_001.yaml`, `paper_trading_config.yaml`) requiring zero switch hits
- `research/tsmomentum_same_session_vol_correction.py` — same
- `tests/test_tsmomentum_vol_estimate_consolidation.py` — same + new exception and invariant tests
- `tests/test_tsmomentum_same_session_vol_correction.py` — same + new exception and invariant tests
- Main report regenerated: OVERALL: PASS, `no_config_file_sets_the_switch` PASS (0 non-corrected), `corrected_config_is_specification_only_exception` PASS, `no_record_feeding_config_sets_the_switch` PASS (0 record-feeding)
- All 6 targeted tests pass; committed at HEAD 6f36269; git status clean; committed diffs empty

**Tests:** `tests/test_tsmomentum_same_session_vol_correction.py` — 17 passed.

## Next task (bounded)

Run the full test suite to confirm all tests pass:
```bash
python -m pytest -q
```

If green, the Cycle 927/928 work is complete and the next cycle should investigate new market opportunities per AGENTS.md Market Opportunity Search (inventory real data and costs, compare plausible candidates, score against data quality, structural mechanism, net capture, automation, diversification, statistical testability).

## Validation commands
```bash
python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py tests/test_tsmomentum_same_session_vol_correction.py
python -m pytest -q
git status --porcelain
git diff --stat -- research/reports/tsmomentum_vol_estimate_consolidation_001.md research/experiments/tsmomentum_vol_estimate_consolidation_001.md config/ data/processed/paper_trading_state.yaml
```

## Scope boundaries
- `data/` and `config/` read-only except the new state file and new config file for the corrected record
- No committed record, committed config, or committed paper-trading state may be modified
- No live trading, no fetcher call, no new dependency
- The committed record stays published and NO-GO; the corrected record starts fresh (126 sessions)
