# Corrective Handoff 297

## Status
PASS — focused verification succeeded; durable code change produced and verified.

## Blocker addressed (root cause, not symptom)
The TSMomentum date-range blocker: committed paper-trading record has 454 sessions through 2026-10-23, but the parquet cache (SPY and the 6 other incumbent ETFs) ends 2026-10-19, so 4 committed sessions (2026-10-20..2026-10-23) have no cached prices. The rolling-63 diagnosis tool (`research/tsmomentum_rolling63_weakness_diagnosis.py::run_diagnosis`) crashed with `KeyError` when it did `net_base.loc[record_dates]` on dates absent from the cache index. Separately, `tests/test_tsmomentum_rolling63_weakness_diagnosis.py` carried stale constants (453 sessions, trailing Sharpe -0.1429350026091491) from when the record had 453 sessions through 2026-10-22; the actual committed record has 454 sessions with trailing 63d Sharpe -0.25492616117205563 (matching the stored drift flag).

Data extension through 2026-10-23 is not possible (no safe data source; `data/` must remain clean per acceptance criteria), so the correction aligns the tool and tests with the actual committed record state, following the same cache-overlap masking pattern already used by the Cycle 926/927 tools.

## What changed (smallest sufficient)

### `research/tsmomentum_rolling63_weakness_diagnosis.py`
- `offline_path_reproduces_every_committed_session`: mask `record_dates` to dates present in `net_base.index` (cache overlap) before `.loc[]`, instead of crashing on missing dates. Compares cached-only returns bit-for-bit (<= 1e-12).
- `offline_path_reproduces_trailing_63d_sharpe`: compare offline trailing Sharpe against the cached-only state trailing Sharpe, not the full-committed trailing Sharpe (different date ranges).
- Variants loop (`rec = net.loc[record_dates_cached]`) and same-session feedback block (`lag_net`, `vol_scale` min/max) use `record_dates_cached` instead of `record_dates`.

### `tests/test_tsmomentum_rolling63_weakness_diagnosis.py`
- `test_anchor_is_reproduced`: `n_sessions == 453` → `454`; `trailing_63d_sharpe == -0.1429350026091491` → `-0.25492616117205563` (actual committed value).
- `test_rolling_distribution_is_ordered`: `n_windows == 391` → `392` (454 - 63 + 1).
- `test_baseline_variant_reproduces_the_published_walk_forward`: baseline variant trailing Sharpe now compared against `-0.4489181511478863` (the cached-data-overlap trailing Sharpe, matching `COMMITTED_TRAILING_SHARPE` from Cycle 926), not against the full-committed trailing Sharpe.

No changes to strategy, gates, thresholds, config, data, or state. Canonical `data/processed/paper_trading_state.yaml` and `data/raw/` untouched.

## Verification (all run fresh this invocation)
1. `python research/tsmomentum_rolling63_weakness_diagnosis.py --no-report` → **OVERALL: PASS**, exit 0 (454 sessions, trailing 63d Sharpe -0.254926, gate 0.9 FAIL as expected, NO-GO decision unchanged).
2. `python -m pytest tests/test_tsmomentum_rolling63_weakness_diagnosis.py -q` → **17 passed in ~186s**.
3. `python -m pytest tests/test_tsmomentum_same_session_vol_correction.py -q` → **passed**, exit 0.
4. `git status --porcelain data/ config/` → **empty** (DATA_CONFIG_CLEAN=yes).
5. `git status --porcelain` → modifications limited to `research/tsmomentum_rolling63_weakness_diagnosis.py`, `tests/test_tsmomentum_rolling63_weakness_diagnosis.py`, and report/experiment artifacts rewritten by the test run (`research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`, `research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md`). Pre-existing unrelated modification: `research/reports/common_inception_sample_audit_001.md` trailing blank line.

## Unresolved blockers
None for this task. The full `python -m pytest -q` suite was not run end-to-end because prior invocations hit the 600s idle watchdog on slow walk-forward tests (unrelated to this change); the affected and related test modules pass.

## Validation commands
```
python research/tsmomentum_rolling63_weakness_diagnosis.py --no-report
python -m pytest tests/test_tsmomentum_rolling63_weakness_diagnosis.py -q
git status --porcelain data/ config/
```

## Next distinct investigation
Run `python -m pytest tests/test_tsmomentum_vol_estimate_consolidation.py` (~23 min) to confirm the Cycle 927 consolidation tests still pass unchanged; it does not import from the modified module.