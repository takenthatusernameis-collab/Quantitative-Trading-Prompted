# NEXT_AGENT_TASK.md

## Cycle 903 — Measure the promotion evidence on the sample the frozen configuration describes (the ragged cross-section)

### Context

Cycle 902 (see `research/reports/sample_definition_hygiene_001.md`) made the
long-sample promotion artifact publish **the sample it actually computed**:
the label (the common inception, 2004-11-18) next to the realized window (the
union calendar of the raw cache, 1993-01-29..2026-10-19, 8,488 sessions), with
the realized window derived independently from `data/raw/*.parquet`, a
run-time-derived cache fingerprint and re-derived reference-sample anchors.
Every published number, gate, threshold and decision was left untouched.

That publication exposes the question this cycle takes up: **which of the two
windows is the decision-relevant one?**

`src/backtest/engine.py:run_backtest` does not slice the price frame it
loads (`src/data/yfinance_fetcher.py` returns the whole parquet; the engine
only does `close.ffill().dropna(how="all")`), and
`src/features/momentum.py:select_top_decile` selects the single best asset
when fewer than five assets have a momentum value and otherwise ranks the
*available* assets. The realized long sample therefore carries a **ragged
cross-section**:

| from | cross-section |
|---|---|
| 1993-01-29 | SPY (1 asset) |
| 1999-03-10 | + QQQ (2) |
| 2000-05-26 | + IWM (3) |
| 2001-08-27 | + EFA (4) |
| 2002-07-30 | + TLT (5) |
| 2003-04-14 | + EEM (6) |
| 2004-11-18 | + GLD (7) |

The published long-sample evidence of the incumbent
(`tsmomentum_spytrend_001`, `config/simulation_candidate_001.yaml`) is
therefore the numbers of a **1-to-7-asset** strategy — canonical Sharpe
0.5657179297830458, max DD -0.6224126346564325, PSR 1.6549061233035153e-08,
failed gates `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown',
'psr']`, decision NO-GO — while the frozen configuration describes a 7-asset
universe whose first fully populated date is 2004-11-18, the date the artifact
published as its `start_date` until Cycle 902. **The incumbent's long-sample
evidence has never been measured on a window in which all seven assets
exist.**

### Objective

Measure, read-only and without changing any gate, threshold, configuration or
committed number, the incumbent's canonical metrics and its **full promotion
gate table** on the **common-inception sample** (2004-11-18..2026-10-19, seven
assets throughout) and publish them next to the union-sample numbers, so that
it is known whether the NO-GO verdict and the published numbers are an
artefact of the sample definition.

### Acceptance criteria

1. A new read-only, deterministic tool `research/common_inception_sample_audit.py`
   (exit 0 with `OVERALL: PASS`) computes the incumbent's path on the
   common-inception sample by **slicing the aligned price frame** to
   2004-11-18 before the same signal, cost model, universe, lookback / skip /
   top_fraction and rebalance semantics are applied (the same code path as
   `research/promotion_feasibility_backtest.py`; **no change to
   `src/backtest/engine.py`**), and publishes for **both** samples: the
   canonical Sharpe, max drawdown, rolling-63d Sharpe, rolling-63d max
   drawdown, PSR (seed 20240101, target 1.4178), the gate table and the
   decision.
2. The **cross-section width** of each sample is published (the number of
   assets with a price on each session: minimum, median, maximum, and the
   dates on which the width changes), so that the raggedness of the union
   sample is visible in the artifact.
3. The committed artifact `research/reports/promotion_feasibility_backtest_001.md`
   and every number in it are **not** modified; the new measurement is
   published in a new artifact.
4. The verdict is stated explicitly, and it is a **measurement, not a
   decision**: if the two samples disagree about any gate or about the
   decision, the difference is reported as a *sample-definition sensitivity*;
   the incumbent's published decision (NO-GO) is **not** changed by this
   cycle, and the choice of the sample on which the promotion gates are
   evaluated is left to an explicitly recorded decision, with the evidence
   needed for it published here.
5. A test asserts that the new tool is **read-only** (no file under `data/`
   or `config/` changes), **deterministic** (two runs agree bit-for-bit) and
   that the union-sample numbers it publishes equal the committed artifact's
   numbers exactly.

### Validation commands

```
python research/common_inception_sample_audit.py  # OVERALL: PASS, both samples published
python research/promotion_feasibility_backtest.py # OVERALL: PASS, decision=NO-GO, failed gates unchanged
python research/rolling_63d_gate_refresh.py       # OVERALL: PASS, 12/12 checks, decision NO-GO
python research/rebalance_schedule_audit.py       # OVERALL: PASS, 12/12 checks
python research/long_sample_overlay_attribution.py # OVERALL: PASS
python research/go_no_go_evaluation.py            # decision NO-GO, failed gates ['rolling_63d_sharpe', 'psr']
python -m pytest -q                               # whole suite green
git status --porcelain data/ config/              # empty
```

### Scope boundaries

* Do **not** change `src/backtest/engine.py`: the window semantics stay as
  they are, and the slicing happens inside the new read-only tool. This is
  the decision Cycle 902 explicitly deferred.
* Do **not** change a gate, a threshold, the decision mapping, a candidate
  configuration, a universe, the cost model or the Sharpe convention.
* Do **not** re-optimise, re-fit or re-select the incumbent, and do not start
  a new candidate family; this is a measurement of the existing candidate.
* Do **not** promote, retire or re-decide the incumbent in this cycle.
* If a metric of the committed artifact moves, stop and report it instead of
  regenerating the published artifacts around the new value.
