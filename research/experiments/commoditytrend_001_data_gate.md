# Experiment: commodity data gate for `commoditytrend_001` (Cycle 949)

**Hypothesis reference:** `research/hypotheses/commoditytrend_001.md` (v001, frozen in Cycle 947); frozen configuration `config/commoditytrend_001.yaml`.

**Objective:** measure the pre-registered *data gate* of the frozen candidate -- the common inception and the fold count of the frozen 10y/12m/6m walk-forward design -- on the **upstream** history of the frozen universe, fetched into a scratch directory only. This is a data-readiness measurement; it publishes no trading verdict and it changes no rule, universe, benchmark, cost model or gate.

## Data used

- **Source:** yahoo_finance (the repository's own source, `src/data/yfinance_fetcher.py`), price field `Close`, `auto_adjust=False` -- the same convention as the committed cache.
- **Retrieval date:** 2026-10-22 (UTC). Request window `2000-01-01 .. 2026-10-22`.
- **Universe:** `DBC`, `BNO`, `UNG`, `GLD`.
- **Frequency:** daily. **Location:** the scratch directory `/tmp/scratchpad/commodity_fetch` only; the committed cache is not rewritten.

| Symbol | Rows | First | Last |
|---|---|---|---|
| `DBC` | 5210 | 2006-02-06 | 2026-10-21 |
| `BNO` | 4123 | 2010-06-02 | 2026-10-21 |
| `UNG` | 4910 | 2007-04-18 | 2026-10-21 |
| `GLD` | 5515 | 2004-11-18 | 2026-10-21 |

**Point-in-time treatment:** the panel is the instrument's own history as the source publishes it; no constituent membership is involved and no series is back-filled. The panel is only usable point-in-time once it is committed: until then it is a measurement of what the source holds.

## Configuration

- **Walk-forward design (frozen):** 10y train / 12m test / 6m step, 21-day purge, 21-day embargo, identical to the incumbent's `WF_*` constants and to `src/evaluation/walkforward.py`.
- **Gate (frozen):** at least 10 folds, i.e. 3906 business days, i.e. a common inception on or before 2011-10-20.
- **Cost model:** not used -- this measurement runs no backtest.
- **Parameters varied:** none. One universe, one design, one measurement.

## Results

| Quantity | Value |
|---|---|
| Common inception | **2010-06-02** |
| Common end | 2026-10-21 |
| Business days available | 4276 |
| Business days required for 10 folds | 3906 |
| Folds (business-day calendar) | **12** |
| Folds (traded-session calendar) | **11** |
| Gate | **PASS** |

The committed cache's 2015-01-02 common start is confirmed to be a **fetch window**: the upstream history of `BNO` reaches back to 2010-06-02 and of `UNG` to 2007-04-18, and on every session where the upstream history and the committed cache overlap the closes are identical.

## Number of trials

**1.** This is a measurement of a pre-registered gate, not a search: no configuration was tried, no parameter was tuned and no backtest was run. The candidate's declared trial count (3, for the Deflated Sharpe Ratio of the future evaluation) is untouched.

## Reproduction

```bash
python research/commodity_data_gate_fetch.py
python research/commodity_data_gate_001.py
python -m pytest -q tests/test_commodity_data_gate_001.py
git status --porcelain data/ config/
```

The tool is read-only with respect to the repository: `data/` and `config/` are fingerprinted before and after the run and must be byte-identical.

## Decision

**Data readiness: the gate PASSES.** The candidate is no longer blocked by the data gate *in principle*; it remains **Blocked by data/infrastructure** in practice until the extended panel is committed and the frozen evaluation is run. **No trading verdict is published in this cycle.**
