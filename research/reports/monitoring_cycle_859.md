# Monitoring Cycle 859 — verification-only tick + two reproducibility fixes

- **Cycle:** 859 (post-gate monitoring, verification-only mode)
- **Run date:** 2026-10-19 (UTC 15:25–15:32Z)
- **Mode:** verification-only — **no new completed US trading session** existed beyond 2026-10-16, so the paper-trading state was **not** extended.
- **State touched:** none. `data/processed/paper_trading_state.yaml` and `data/raw/*.parquet` are byte-identical before and after the cycle (SHA-256 compared over 21 files).

## 1. Precondition check (was a new completed session available?)

Current UTC time at the start of the cycle was **2026-10-19 15:25Z = 11:25 ET (Monday)**. The market-close guard in
`research/extend_paper_trading_state.py` treats a session as complete only once the local clock passes
`close_hour + 1` (16:00 + 1h slack) on the session date, or on a later local day.

Evidence collected:

| Check | Result |
|---|---|
| Raw cache index max date (SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX) | **2026-10-16** for all 8 symbols (row counts unchanged: 8487 / 6945 / 6637 / 6094 / 5512 / 6322 / 5916 / 451) |
| Provider bar for 2026-10-19 (yfinance, SPY) | present but **partial** (volume 11,726,379 vs ~25–64M on closed days; session still open at 11:25 ET) |
| `python research/refresh_raw_cache.py --dry-run` | `no-op: no completed sessions to append` — 0 rows appended for every symbol; the 2026-10-19 bar was dropped by `complete_session_view` |
| `python research/extend_paper_trading_state.py --dry-run` | `no new completed session`; sessions extended 0; state write count 0; NAV before = NAV after = 133,729.224310211 |

**Conclusion:** no completed session beyond 2026-10-16 → verification-only mode. The extension path was *not* taken;
both session-safe tools were used in dry-run mode, which downloads into a scratch directory and never writes the
canonical `data/raw` cache or the state file.

## 2. Defects found while executing the documented validation commands

### 2.1 The documented go/no-go command did not run

`python research/go_no_go_evaluation.py` (the command listed in the Cycle 859 acceptance criteria and in
`research/reports/go_no_go_evaluation_002.md`) aborted with:

```
ModuleNotFoundError: No module named 'src'
```

Running `python research/<script>.py` puts the *script's* directory on `sys.path`, not the repository root, so the
`src` package was not importable. Every sibling research script (`drift_persistence_report.py`,
`extend_paper_trading_state.py`, `refresh_raw_cache.py`, `run_cycle*.py`) already inserts the repository root into
`sys.path`; `go_no_go_evaluation.py` was the only one that did not.

**Fix:** added the same `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` bootstrap before the `src`
imports. The tool now runs exactly as documented, with no `PYTHONPATH` help.

**Hardening:** the script now also loads the committed thresholds from `config/paper_trading_config.yaml`
(`PaperTradingConfig.from_paper_config_yaml`) instead of relying on library defaults, so future config drift cannot
silently diverge from the evaluation.

### 2.2 The PSR gate number was not reproducible

`evaluate_go_no_go` called `compute_psr` **without a seed**, so the moving-block bootstrap behind the PSR gate drew
a fresh random resample on every run. Two evaluations of the *same* committed state produced different gate inputs:

| Run | `psr_normal` | `sharpe_se` | 95% CI |
|---|---|---|---|
| Cycle 858 report (`go_no_go_evaluation_002.md`) | 0.621679 | 0.710598 | [0.378, 3.114] |
| Cycle 859, first run (unseeded) | 0.627490 | 0.677122 | [0.387, 3.127] |

The *decision* (INCONCLUSIVE, grey zone 0.5–0.95) was unaffected, but the recorded evidence was not reproducible and
near a threshold the decision itself could flip between runs. This contradicts the reproducibility requirement in
`AGENTS.md` ("Evidence artifacts … reproduction commands").

**Fix:** `GoNoGoConfig` gained an explicit `psr_seed` (default `DEFAULT_PSR_SEED = 20240101`), which is passed to
`compute_psr`. No threshold, gate, strategy parameter, cost model or universe was changed — only the *sampler seed*
of the estimator. The tool now evaluates the record twice and prints `evaluation_deterministic: True/False`
(exit code 1 when the two runs disagree), so non-determinism can no longer pass silently.

**Post-fix value (stable, reproduced byte-identically across separate processes):**

| Metric | Value |
|---|---|
| `psr_normal` | 0.625683 |
| `psr_empirical` | 0.654000 |
| `sharpe_se` | 0.687208 |
| 95% CI | [0.344994, 2.998531] |
| `psr_seed` | 20240101 |
| decision | INCONCLUSIVE (unchanged) |

### 2.3 Regression test added

`tests/test_go_no_go_evaluation.py` (4 tests) encodes the invariants as executable checks:

1. the tool runs standalone from the repository root with `PYTHONPATH` removed from the environment;
2. running it leaves the state file, the state backup and every `data/raw/*.parquet` byte-identical;
3. two evaluations of the committed state agree exactly on PSR, empirical PSR, SE, CI and decision;
4. the PSR seed is a fixed integer by default.

## 3. Current evaluation snapshot (unchanged record, 449 sessions through 2026-10-16)

| Metric | Value | Gate | Status |
|---|---|---|---|
| `paper_days` | 449 | ≥ 63 | PASS |
| `paper_sharpe` (full period) | 1.638009 | — | — |
| `rolling_sharpe_63d` (report-level gate) | **-0.493001** | ≥ 0.9 | **FAIL** |
| `psr_normal` | 0.625683 | > 0.95 (GO) / < 0.5 (NO-GO) | grey zone → INCONCLUSIVE |
| `paper_max_dd` | -0.049857 | > -0.15 | PASS |
| drift flags | 1 (`low_rolling_sharpe` = -0.21188351222842883, 2026-10-16) | — | active |
| regime persistence | 134 days | ≥ 5 | PASS |
| decision (`evaluate_go_no_go`) | **INCONCLUSIVE** | — | unchanged from Cycle 858 |

Drift persistence (reproducible via `research/drift_persistence_report.py`): **5 consecutive trading days** below the
0.5 threshold (2026-10-12 → 2026-10-16); 21 of 33 sessions below threshold in the trailing 46 calendar days;
recomputed rolling 63d Sharpe equals the stored drift-flag value exactly.

## 4. Verification commands and observed results

| Command | Result |
|---|---|
| `python -m pytest -q` | **46 passed** in 131.91s (42 pre-existing + 4 new) |
| `python research/drift_persistence_report.py` | persistence **5** trading days; `stored == recomputed: True`; exit 0 |
| `python research/_tmp_cycle77_verify.py` | **OVERALL: PASS** (rolling 63d Sharpe match True, regime flips 6/6, NAV $133,729.22, max DD -4.9857%) |
| `python .github/scripts/test_kilo_supervisor_loop.py` | **OK** — 10 tests, 0.414s |
| `python research/go_no_go_evaluation.py` | decision INCONCLUSIVE, `psr_normal 0.625683`, `evaluation_deterministic: True`, `side_effect_free: True`; exit 0 |
| `python research/go_no_go_evaluation.py` (×2, separate processes) | outputs identical (excluding the timestamp line) |
| SHA-256 comparison of state + 20 raw/backup files, before vs after cycle | **byte-identical** |

## 5. Scope compliance

- Monitoring-only: no strategy, config, cost model, universe or gate/threshold was changed.
- No live trading, no credentials, no new dependencies, no workflow/schedule changes.
- The state extension path was *not* exercised (no completed session); the state file was never written.
- Only additive/derived files were produced: `tests/test_go_no_go_evaluation.py`,
  `research/reports/monitoring_cycle_859.md`, plus this report's addendum in `go_no_go_evaluation_002.md`.

## 6. Open item carried forward (not changed in this cycle)

The **report-level rolling-63d-Sharpe gate (≥ 0.9) is still not enforced by the code-level decision function**: a
record with PSR > 0.95 but a negative rolling 63d Sharpe would still be labelled "GO" by `evaluate_go_no_go`. This
is the exact mechanism that produced the earlier unqualified "GO for live deployment" claims in
`research/reports/deployment_dossier_001.md` (reconciled in Cycle 858). Changing it alters a *gate*, so it is out of
scope for a monitoring cycle and is proposed as the next bounded task.
