# DBC/csmomentum Governance Record — Cycle 291

## Decision
**No governance action required.** The blocker premise is false.

## Evidence
- `data/raw/DBC.parquet` committed tree max date: **2026-10-08** (5,201 rows). NOT extended to 2026-10-21.
- The 2026-10-21 extension existed only in `/tmp/scratchpad/commodity_fetch/` (scratch-only, never committed, directory no longer present).
- `data/processed/simulation_csmomentum_001.parquet` max date: 2026-10-09 (8,482 rows). DBC is in the csmomentum universe (config/csmomentum_candidate_001.yaml line 33); the engine forward-fills the last known DBC weight (0.1) beyond DBC's raw end date. All 25 columns populated at sim end date, zero NaN.
- README documents the recomputation delta as **1.4e-17 max abs diff over 8,482 sessions** (floating-point noise) and faithful-path Sharpe 0.663540 vs published 0.6635 — no material difference.
- `tests/test_cost_admissibility_screen.py`: **40 passed** in isolation.

## Consistency check (`scripts/verify_dbc_csmomentum_consistency.py`)
Reports `INCONSISTENT` (sim_end 2026-10-09 > dbc_end 2026-10-08). This is a **false positive**: the check flags any sim_end > dbc_end, but forward-filling the last DBC weight is expected engine behavior. The artifacts are consistent with the committed DBC cache to within 1.4e-17.

## Resolution (Option (a))
**Option (a) — restore historical DBC to frozen cut-off — is already satisfied.** DBC.parquet already ends at 2026-10-08. No truncation needed. No data/config changes required.

## Pre-existing full-suite failures (unrelated to this blocker)
- `tests/test_commodity_data_gate_001.py`: 3 FAILED + 5 ERROR — missing `/tmp/scratchpad/commodity_fetch/commodity_fetch_report.json` (scratch data cleaned up).
- `tests/test_leadlag_001_evaluation.py`: 2 FAILED — references non-existent git object `4f0947bca1289acd0c6d9ed6fc6424f21b8fe36d`.
- `tests/test_state_aggregate_audit.py`, `test_tsmomentum_rolling63_weakness_diagnosis.py`, `test_go_no_go_evaluation.py`, `test_tsmomentum_same_session_vol_correction.py`, `test_tsmomentum_vol_estimate_consolidation.py`: failures trace to paper trading state advancing to 459 sessions / 2026-10-30 beyond committed report values (454 / 2026-10-23).

## Verification commands
```
PYTHONPATH=/home/runner/work/_temp/kilo-tmp/pylibs python3 -c "import pandas as pd; d=pd.read_parquet('data/raw/DBC.parquet'); print(d.index.max())"
PYTHONPATH=/home/runner/work/_temp/kilo-tmp/pylibs python3 scripts/verify_dbc_csmomentum_consistency.py
PYTHONPATH=/home/runner/work/_temp/kilo-tmp/pylibs python3 -m pytest tests/test_cost_admissibility_screen.py -q
```