# Next Agent Task: Cycle 6 - Validation of the Promoted SPY Trend Filter Candidate

## Context

Cycle 5 applied two **pre-specified** regime filters on top of the Cycle 4 best
configuration (226-day TSMOM + combined volatility-targeting 10% + drawdown
control 15%), using the hypothesis-documented **3 bps round-trip** cost model.

### Cycle 5 Key Findings

| Candidate | Test Sharpe (2018-2026) | Max DD | Trades | Meets 0.9 gate? |
|-----------|-------------------------|--------|--------|-----------------|
| Unfiltered (Cycle 4 best) | 0.746 | -16.6% | 1,812 | No |
| **SPY Trend Filter** (cash when SPY < 200d SMA) | **1.418** | -7.8% | 1,196 | **YES** |
| VIX Filter (50% when VIX > 30) | 1.046 | -12.3% | 1,768 | YES |
| Sector ETFs (alternative universe) | 0.442 | -15.1% | 1,964 | No |
| Global Asset Classes (alternative universe) | 0.552 | -15.2% | 1,717 | No |

**Classification: Credible Candidate (preliminary)** — the SPY Trend Filter
promotes the strategy to the promotion gate.

### Important caveat carried over from Cycle 5

- The promotion gate is a **preliminary screening gate only** (per AGENTS.md).
  The result rests on a **single 2018-2026 test block** and the **single 200-day**
  SMA parameter — it has not been independently validated across time or
  parameter neighbors.
- Cycle 4's documented combined-overlay Sharpe (0.779) was computed with an
  under-applied cost model in `src/evaluation/risk.py` (effective ~0 bps; the
  report itself states "0.0 bps"). Cycle 5 corrected this to 3 bps and showed the
  gate conclusion is robust to the cost correction (SPY filter 1.42 correct-cost).
  A bounded non-blocking correction to `src/evaluation/risk.py` is recommended
  (see Recommended Follow-up).

### Artifacts produced by Cycle 5

- `research/run_cycle5.py` (pipeline script)
- `research/experiments/tsmomentum_regime_001.md`
- `research/experiments/tsmomentum_regime_filter_001.md`
- `research/experiments/tsmomentum_universe_001.md`
- `research/reports/tsmomentum_decision_003.md`
- `research/hypotheses/tsmomentum_004.md`

### Evidence this task builds on

- Regime analysis shows the strategy is strongly regime-conditional: in bear
  regimes (SPY < 200d SMA) the unfiltered Sharpe is **-1.37**, while in bull
  regimes it is **+1.67**. The 200d-SMA trend filter removes the bear-regime days
  (≈20% of test days) where the strategy loses money — a well-documented effect
  (TSMOM momentum crashes during bear markets; trend filters mitigate them).

---

## Objective

Validate that the Cycle 5 promoted candidate is **not** a single-period or
single-parameter artifact before advancing to simulation/paper-trading.

The candidate under validation:
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (baseline 7-asset)
- Signal: 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5)
- Risk overlay: combined vol-targeting (10%) + drawdown control (15%)
- Regime filter: SPY 200d-SMA trend filter (0% exposure when SPY < 200d SMA)
- Cost model: 3 bps round-trip (correct, as in Cycle 5)

Produce a **walk-forward test** of this candidate and a **parameter-plateau check**
of the SMA trend-window, then decide whether to advance or downgrade.

---

## Acceptance Criteria

The Cycle 6 work must produce:

1. **`research/experiments/tsmomentum_regime_filter_wf_001.md`** containing:
   - A walk-forward evaluation of the SPY trend-filter candidate:
     expanding or rolling 10-year training window, 1-year forward test,
     6-month step, purge = 21 days, embargo = 21 days (reuse the design in
     `src/evaluation/walkforward.py` and `tsmomentum_walkforward_001.md`).
     Parameters are **fixed** (no per-fold re-optimization).
   - Reported metrics per fold and in aggregate: train Sharpe, test Sharpe,
     test annualized return, test max drawdown, test trade count.
   - Aggregate: number of folds, **mean test Sharpe**, **% folds with Sharpe > 0**,
     mean test max drawdown, total pooled OOS trades.
2. **Parameter-plateau check** of the SMA trend window (same test-period
   2018-2026, same candidate config, correct 3 bps costs) for SMA windows
   `{150, 175, 200, 226, 250, 277}`:
   - Table of (SMA window, test Sharpe, test max DD, trades).
   - Plateau verdict: the 200d result is "robust" if **>= 2 of the 6 windows**
     (including 200d) achieve Sharpe >= 0.9, i.e. the gate is not won or lost
     on the single 200d value.
3. **Promotion-gate verdict** (final):
   - If mean walk-forward OOS Sharpe >= 0.9 **AND** >= 50% of folds positive
     **AND** the SMA plateau check holds -> the candidate is confirmed
     **Credible Candidate**; next cycle advances to simulation/paper-trading.
   - Otherwise the candidate is **downgraded to Exploratory Signal** and the
     next cycle must explore a **different structural mechanism** (do NOT
     continue regime/universe variations on TSMOM).

---

## Implementation Notes

### Pre-specified validation design (no cherry-picking)
- SMA trend windows are **fixed a priori**: `[150, 175, 200, 226, 250, 277]`.
- Walk-forward windows reuse the Cycle 3 design exactly (10-year rolling train,
  1-year test, 6-month step, purge=21, embargo=21) — only the candidate config
  (added 200d SMA filter) changes from Cycle 3's unfiltered baseline.
- The filter is applied as a 0/1 exposure multiplier on the 226-day momentum
  test-period weights, **before** the combined vol+dd overlay (same as Cycle 5),
  so walk-forward folds are directly comparable to the 0.746 / 1.418 figures.

### Cost model
- Use the **correct 3 bps round-trip** cost model throughout (commission 1 bps +
  slippage 2 bps). Cycle 5's `_apply_overlay` in `research/run_cycle5.py` already
  implements this correctly. Reuse or replicate it in Cycle 6.
- Do NOT use `src/evaluation/risk.py::combined_risk_overlay` for the costed
  overlay (that path has the under-costing defect); either reuse Cycle 5's
  `_apply_overlay` or apply `cost_per_trade = commission_bps + slippage_bps`
  (bps already returned as fractions by `get_cost_params`).

### Data
- Baseline universe + SPY + ^VIX already cached in `data/raw/` (Yahoo Finance).
- No new data dependencies; Binance/Bybit remain blocked, OKX is available if a
  crypto mechanism is later needed.

### Reuse existing infrastructure
- Reuse `src/evaluation/walkforward.py` helpers (`build_walkforward_splits`,
  `evaluate_walkforward`, `summarize_walkforward`) and `src/evaluation/utils.py`
  (`run_backtest_for_config`, `split_by_periods`, `period_metrics`).
- Add a thin `research/run_cycle6.py` that composes the filtered candidate with
  the walk-forward + plateau logic and writes the report. Do not modify shared
  evaluation modules beyond minimal, behavior-preserving additions.

---

## Scope Boundaries

- **In scope**: walk-forward + SMA-window plateau validation of the SPY trend
  filter candidate only.
- **Do NOT** begin live or paper-trading execution.
- **Do NOT** start additional agent sessions / workflows (no recursive dispatch).
- **Do NOT** add dependencies or new data sources.
- **Do** preserve all existing Cycle 1-5 artifacts.

### Recommended bounded follow-up (non-blocking, separate task)
Fix the overlay-path cost defect in `src/evaluation/risk.py`
(`combined_risk_overlay`, `run_risk_overlays`, `run_combined_risk_overlays`):
`cost_per_trade` should be `commission_bps + slippage_bps` (not divided by 10000
again), matching `utils.run_backtest_for_config`. This would let Cycle 4's
documented combined-overlay figures be recomputed at honest 3 bps costs. This is
**out of scope** for Cycle 6 and should be tracked separately if pursued.

---

## Validation Commands

```bash
# Run Cycle 6 pipeline
python3 research/run_cycle6.py

# Reproduce prior cycles still run without error
python3 research/run_cycle3.py
python3 research/run_cycle4.py
python3 research/run_cycle5.py

# Lint
python3 -m ruff check research/run_cycle6.py src/evaluation/

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle5.py').read()); ast.parse(open('research/run_cycle6.py').read())"

# Artifact existence + content
test -f research/experiments/tsmomentum_regime_filter_wf_001.md
grep -q "Walk-Forward" research/experiments/tsmomentum_regime_filter_wf_001.md
grep -q "Plateau" research/experiments/tsmomentum_regime_filter_wf_001.md
grep -q "Credible Candidate" research/experiments/tsmomentum_regime_filter_wf_001.md
grep -Eq "Sharpe [0-9]" research/experiments/tsmomentum_regime_filter_wf_001.md
```

---

## Expected Outcome

- **If** mean walk-forward OOS Sharpe >= 0.9, >= 50% of folds positive, and the
  SMA-plateau check holds: keep the candidate as **Credible Candidate** and the
  *following* task advances to simulation/parameter optimization + paper-trading.
- **If not**: downgrade this candidate to **Exploratory Signal**; write
  `research/reports/tsmomentum_decision_004.md` documenting the downgrade, and
  the following task must explore a **different structural mechanism** —
  preferably one with an independent, plausible inefficiency and net-capture
  feasibility from available data, e.g. **crypto perpetual funding/carry** on OKX
  (`src/data/yfinance_fetcher.py` + CCXT OKX), where funding-rate history, spot,
  and swap data are all available (see `research/reports/data_inventory.md`).

---

## Evidence Reference

- Cycle 5 promoted candidate: SPY Trend Filter, test Sharpe **1.4178** (correct 3 bps)
  (source: `research/experiments/tsmomentum_regime_filter_001.md`,
   `research/reports/tsmomentum_decision_003.md`)
- Cycle 4 documented (under-costed) best combined Sharpe: 0.7794
  (source: `research/experiments/tsmomentum_combined_risk_001.md`)
- Cycle 3 walk-forward template: mean test Sharpe 0.679, 97.9% positive folds
  (source: `research/experiments/tsmomentum_walkforward_001.md`)
- Regime-conditional Sharpe: bear regime -1.37, bull regime +1.67
  (source: `research/experiments/tsmomentum_regime_001.md`)
- Code base: `98fe0e3` (HEAD includes Cycle 5 additions + `src/evaluation` lint fixes)
