# Cycle 950 — Commit the extended commodity panel and run the frozen `commoditytrend_001` evaluation

## Context
- Cycle 949 measured the pre-registered data gate of `commoditytrend_001` on **upstream** history fetched into a scratch directory only (`/tmp/scratchpad/commodity_fetch/`, not committed): the gate **PASSES** — common inception **2010-06-02** (deadline 2011-10-20), 4,276 business days vs 3,906 required, **12 folds** on the business-day calendar and **11 folds** on the traded-session calendar, both >= the 10 the gate requires.
- The scratch fetch confirmed the committed cache's 2015-01-02 start is a **fetch window**, not instrument history: on every overlapping session the closes are byte-identical (DBC 5,201/5,201, BNO 2,964/2,964, UNG 2,964/2,964, GLD 5,513/5,513). The upstream history **extends** BNO by 1,155 sessions (2010-06-02..2014-12-31) and UNG by 1,942 sessions (2007-04-18..2014-12-31); DBC and GLD were already complete in the cache.
- The hypothesis (`research/hypotheses/commoditytrend_001.md`) and configuration (`config/commoditytrend_001.yaml`) remain **frozen** (Cycle 947) and the candidate is still **Blocked by data/infrastructure**: the extended panel is not in the committed cache, so the frozen evaluation has never been run and **no trading verdict exists**.

## Objective
Close the data-readiness gap by committing the extended panel under the repository's own fetcher convention, then run the **frozen** `commoditytrend_001` evaluation and publish the pre-registered result — or the falsification conditions that fire. No gate, threshold, cost model, universe, Sharpe convention, parameter or decision mapping may be changed after a result is known.

## Acceptance criteria
1. `data/raw/BNO.parquet` and `data/raw/UNG.parquet` are extended to their upstream starts (BNO -> 2010-06-02, UNG -> 2007-04-18); `data/raw/DBC.parquet` and `data/raw/GLD.parquet` are byte-identical to the committed cache (already complete). The extension is produced by the repository's own fetcher convention (`src/data/yfinance_fetcher.py::_download`: `auto_adjust=False`, `group_by="ticker"`, `str.title` columns, UTC index, dedup/sort), not by a bespoke writer.
2. The overlap between the new frames and the previously committed cache is **byte-identical** (every overlapping Close value equal, max abs diff 0), verified by the commit tool before the write.
3. The committed four-instrument panel has common inception **2010-06-02** and the data gate still passes (>= 10 folds on both calendars).
4. The frozen evaluation is run **config-faithful**: 10y train / 12m test / 6m step, 21-day purge and embargo, long-only 252/21 absolute time-series momentum, equal weight across held assets, cash otherwise, 3.0 bp/unit cost model, benchmark = 1/N equal-weight of the same four instruments, one trial, no grid.
5. Published per the pre-registered falsification conditions: walk-forward gate table (mean/median OOS Sharpe, positive-fold rate, pooled OOS trades); benchmark-relative net excess with its moving-block bootstrap 95% CI (block 4, 2,000 draws, seed 20240101); measured gross capture fraction against the cost hurdle; the expense-ratio band (0.40-0.85 %/yr) reported beside the primary net figure; the post-2010 sub-period; realized turnover and cost drag; Deflated Sharpe Ratio at the declared trial count 3.
6. The verdict is published as **Rejected/Failed**, **Credible Candidate**, or **Blocked** per the pre-registered mapping, with the falsification conditions that fire named explicitly. If any condition fires, the candidate is not promoted and no variant is opened.
7. `git status --porcelain data/ config/` is empty after the commit (only the two parquet files and the new records/tools changed).
8. `python -m pytest -q` passes (full repository suite), and the new cycle's tests pass.

## Scope boundaries
- No new commodities, no new universe members, no parameter grid, no re-tuning, no re-scoring.
- The shared `config/settings.yaml` cost model is **not** touched; the candidate's own `config/commoditytrend_001.yaml` cost section is not touched.
- No live trading, no paper-trading record, no promotion.
- The scratch fetch under `/tmp/scratchpad/commodity_fetch/` is read-only input; it is not copied into the repository by a bespoke path.

## Validation commands
- `python research/commit_commodity_cache.py` -> OVERALL: PASS, exit 0
- `python research/commoditytrend_001_evaluation.py` -> OVERALL: PASS, exit 0, `VERDICT|...`, `FROZEN_CONDITIONS_FIRED|...`
- `python -m pytest -q tests/test_commit_commodity_cache.py tests/test_commoditytrend_001_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`