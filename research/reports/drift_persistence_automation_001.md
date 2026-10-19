# Drift-Flag Persistence Automation — `low_rolling_sharpe` (Cycle 857)

**Generated:** 2026-10-19T15:20:00Z
**Scope:** Monitoring/verification tooling only. No strategy, cost-model, universe or configuration change.
**Status:** Implemented and verified.

---

## 1. Problem

`research/reports/drift_flag_escalation_001.md` §3 established that the
`low_rolling_sharpe` **persistence count quoted in the cycle reports was not
reproducible from the stored data**:

- The documented definition is "consecutive trading days below the 0.5
  threshold".
- The recomputed value on the committed state is **5** consecutive trading days
  (2026-10-12 → 2026-10-16), not the ">20 days" repeatedly quoted in the
  README; 20 was a calendar-day count since the first flagged date.
- No code computed the counter: "the count is recorded manually in
  documentation" (escalation report §3).

Manual counters drift: the same state was described with mutually inconsistent
persistence figures across cycles. A monitoring metric that cannot be
recomputed from the data it describes cannot support a decision.

## 2. Change

### 2.1 `src/evaluation/drift.py` (new)

Pure, deterministic helpers (no I/O, no network):

| Function | Purpose |
|---|---|
| `annualized_sharpe(returns)` | `mean(r) * 252 / (std(r, ddof=1) * sqrt(252))` — identical to the live formula in `src/simulation/paper_trading.py` |
| `rolling_sharpe_series(dates, returns, window=63, min_periods=20)` | Rebuilds the rolling Sharpe for **every** session, reproducing the live gating (`None` before 20 returns exist) |
| `subthreshold_streak(series, threshold=0.5)` | Trailing count of sessions below the threshold |
| `sharpe_persistence(dates, returns, ...)` | Report-ready summary (streak, streak window, first flagged session, flagged/evaluated counts, last Sharpe) |
| `subthreshold_calendar_window(dates, series, calendar_days=46)` | Sessions below threshold over a trailing calendar window (separates a persistent regime from an oscillating one) |

### 2.2 `src/simulation/paper_trading.py`

The live daily update now records the persistence count inside the drift flag
it already raised:

```python
drift_flags["low_rolling_sharpe"] = {
    "value": rolling_sharpe,
    "threshold": 0.5,
    "date": latest_date,
    "persistence_days": sharpe_persistence_days,
}
```

The flag still fires under exactly the same condition as before
(`rolling_sharpe < 0.5 and len(returns) >= 20`); only the metadata is added, so
the drift decision itself is unchanged. A one-line robustness fix
(`output_dir.mkdir(parents=True, exist_ok=True)`) ensures the artifact
directory exists before the daily parquet files are written.

### 2.3 `research/drift_persistence_report.py` (new)

Read-only reporting tool. It loads the committed state, recomputes the
persistence counter, cross-checks the recomputed rolling Sharpe against the
value stored in `drift_flags.low_rolling_sharpe`, and exits non-zero on a
mismatch. It never writes the state, the raw cache, or any report file, so a
monitoring run cannot mutate the canonical dataset.

### 2.4 `research/_tmp_cycle77_verify.py`

The acceptance-criteria verification harness now also recomputes the
persistence streak independently of `src/evaluation/drift.py` and prints it.
The harness no longer assumes the drift flag is present: when the rolling
Sharpe recovers above 0.5 the flag disappears, and the harness then verifies
that the absence is consistent with the threshold instead of raising.

## 3. Data

| Item | Value |
|---|---|
| Source | `data/processed/paper_trading_state.yaml` (committed paper-trading state) |
| Sessions | 449, daily, 2025-01-02 → 2026-10-16 |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM (`config/simulation_candidate_001.yaml`) |
| Point-in-time | State is append-only, one row per **completed** US session; partial bars are rejected by the Cycle 854/855 session guards |
| Config | window 63 sessions, min history 20 returns, threshold 0.5, annualization 252 |
| Trials | 1 (no parameter search: window/min-history/threshold are taken from the existing live code) |

## 4. Results (state as of 2026-10-16)

Command: `python research/drift_persistence_report.py`

| Metric | Value |
|---|---|
| Rolling 63d Sharpe (recomputed) | -0.21188351222842883 |
| Stored drift-flag value | -0.21188351222842883 (**exact match**) |
| **Persistence (consecutive trading days below 0.5)** | **5** (2026-10-12 → 2026-10-16) |
| Sub-threshold sessions, trailing 46 calendar days | 21 of 33 sessions (2026-08-31 → 2026-10-16) |
| Flagged sessions over full history | 109 of 430 evaluated sessions (first: 2025-02-27) |
| Latest 10 evaluated sessions | 0.9920, 0.9994, 0.4728, 0.1902, 0.9356, 0.4892, 0.3669, 0.1133, 0.3249, -0.2119 |

Both figures reproduce the independent findings of
`research/reports/drift_flag_escalation_001.md` §3 exactly (5 consecutive
trading days; 21 of the last 46 calendar days), which validates the
implementation against an independently derived number.

**Correction to the cycle record:** earlier cycle entries in `README.md`
describe the flag as persisting ">20 consecutive days". Under the documented
definition (consecutive trading days below 0.5) the reproducible value is
**5 trading days**; 20 was a calendar-day count since the first flagged
session. The persistence number quoted from Cycle 857 onward is machine-derived
by `research/drift_persistence_report.py`.

## 5. Verification

- `python -m pytest -q` → **42 passed** (27 pre-existing + 15 new offline tests
  in `tests/test_drift_persistence.py`).
- `python research/drift_persistence_report.py` → recomputed Sharpe equals the
  stored drift flag; streak = 5; exit code 0.
- `python research/_tmp_cycle77_verify.py` → **OVERALL PASS**, now including the
  persistence section.
- `python research/refresh_raw_cache.py --dry-run` → no-op for all 8 symbols
  (cache pinned at 2026-10-16).
- `python research/extend_paper_trading_state.py --dry-run` → "no new completed
  session", 0 sessions extended, 0 state writes (2026-10-19 session still open
  at the time of the run).

## 6. Limitations and known confounders

- The counter is a *description* of the recent return path, not a test of
  structural degradation. A 5-day streak is far below the >20-day persistence
  threshold referenced in the escalation report, so it does not change the
  decision label of `drift_flag_escalation_001.md` §5 ("exploratory signal
  degradation — monitor, do not re-optimize").
- The window (63), the minimum history (20) and the threshold (0.5) are taken
  from the live code and are not re-tuned here; re-tuning them would be a
  research change, not a monitoring change.
- The stored state is the only input. If the state is truncated, the recomputed
  history shortens with it; the tool reports the number of evaluated sessions so
  that truncation is visible.

## 7. Decision label

**Tooling / monitoring defect resolved.** The drift status itself is unchanged:
`low_rolling_sharpe` remains active with the same value
(-0.21188351222842883) and the strategy stays frozen pending evidence of
structural degradation.

## 8. Reproduction commands

```
python -m pytest -q
python research/drift_persistence_report.py
python research/drift_persistence_report.py --json
python research/_tmp_cycle77_verify.py
python research/refresh_raw_cache.py --dry-run
python research/extend_paper_trading_state.py --dry-run
```
