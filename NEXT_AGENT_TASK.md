# NEXT AGENT TASK — Cycle 889

## Context
The rank-8 data blocker (`cryptofunding_001`, crypto perpetual funding-rate carry) is **resolved**.
The Binance *public data archive* (`data.binance.vision`) is reachable from this environment even
though the live Binance REST API is geo-blocked (HTTP 451) and Bybit is blocked (HTTP 403); it
publishes monthly funding-rate and kline ZIPs, each with a published SHA256 `.CHECKSUM`.

Cached and committed (every archive object SHA256-verified before parsing):
- `data/raw/crypto/{BTC,ETH}_USDT_USDT_funding_binance.parquet` — 7,395 8h funding records per
  symbol, 2020-01-01T00:00:00Z..2026-09-30T16:00:00Z (2,464.7 days), **0 missing 8h periods, 0
  duplicate timestamps, 0 gaps**; schema identical to the Cycle 888 OKX cache.
- `data/raw/crypto/{BTC,ETH}USDT_{spot,perp}_1d_binance.parquet` — 2,465 daily rows per symbol
  (long and short legs).
- `data/processed/crypto/{BTC,ETH}USDT_carry_path.parquet` — the reproducible daily
  spot-long/perp-short return path (2,464 days/symbol, 2020-01-02..2026-09-30) built by
  `research/collect_binance_crypto_funding.py::build_carry_path`.
- `research/reports/binance_crypto_manifest.json` — machine-readable provenance (row counts, coverage,
  interval counts, gap list, per-file SHA256).
- `research/experiments/cryptofunding_002_data.md` — the data record; `tests/test_binance_crypto_funding.py`
  — 15 offline invariant tests, including a cross-venue check against the OKX series (238
  overlapping 8h settlements: same funding sign in 91.2% of periods, median absolute difference
  0.213 bp).

Shortlist rank 8 moved from "Blocked by data" (20/35) to **"Exploratory signal" (23/35)**; the
ranking order is unchanged. **No edge is claimed**: gross carry (+11.59%/yr BTC, +13.57%/yr ETH over
the full span) is *before* all costs and is strongly regime-dependent (+37.3%/yr ETH in 2021 vs
+1.9%/yr in 2026 YTD). The candidate has no cost model, no walk-forward split, no block-bootstrap CI
and no row in `research/cost_admissibility_screen.py`.

## Objective
Run the **net-of-cost evaluation** of `cryptofunding_001` on the cached series, using the
repository's own method, and record the outcome honestly — including a rejection if the edge does
not survive costs. Concretely:

1. **Pre-register the evaluation before running it** (append to `research/hypotheses/cryptofunding_001.md`):
   the rule set to test, the cost model, the chronological splits, the benchmarks, the promotion
   gates, and the falsification condition. Keep the rule set small and fixed — the hypothesis
   document already names two: (a) always-on spot-long/perp-short carry, (b) hold only while
   funding is positive (the stated entry/exit rule). Record the **trial count**.
2. **Cost model (document every number and its source):** Binance spot taker fee on the long leg,
   Binance USDT-margined perp maker/taker fee on the short leg, slippage per leg, margin/financing
   cost on the perp, and funding rounding. State whether the strategy is held constant-notional
   (one entry + daily drift rebalance) and compute the **annual turnover in weight-change units**,
   so it plugs into the repository's flat `3 bp per unit of weight change` model used by
   `research/cost_admissibility_screen.py`.
3. **Evaluation:** daily gross and net return paths; benchmark = hold spot only (and risk-free);
   chronological train/validation/test split with no post-hoc window exclusion (2020-2021 must stay
   in the record, and a separate **post-2022 sub-sample** must be reported because the hypothesis's
   falsification condition names it); block-bootstrap CI on the net annualized return (126-day
   blocks, 2000 draws, fixed seed — follow `research/experiments/futuresbasis_002.md`);
   multiple-testing control (probabilistic/deflated Sharpe or a permutation test over the rule
   variants); net Sharpe/Sortino, max drawdown, turnover, trade/rebalance count, tail risk.
4. **Extend the cost screen** with a row for this candidate (extend `research/cost_admissibility_screen.py`,
   do not duplicate it), so the candidate gets the same break-even-cost and gate-headroom treatment
   as ranks 1, 2, 3, 4, 6 and 10. The screen must still print `OVERALL: PASS`.
5. **Publish and re-state the verdict:** update `research/hypotheses/cryptofunding_001.md`,
   `research/reports/opportunity_shortlist.md` (rank-8 row, cost column and the C8 section),
   `research/reports/data_inventory.md`, and write `research/experiments/cryptofunding_002_evaluation.md`
   with data, splits, configuration, metrics, trial count and reproduction commands.

## Acceptance Criteria
- The candidate is evaluated **net of a documented cost model**; gross-only numbers are not
  presented as a result.
- Net metrics reported for both symbols and both rule variants: annualized net return, net Sharpe,
  Sortino, max drawdown, annual turnover, rebalance count, and a block-bootstrap CI on the net
  annualized return; the promotion gate (net OOS Sharpe >= 0.9 and > 100 pooled OOS trades) is
  applied and reported explicitly as pass/fail.
- The post-2022 sub-sample result is reported separately (the pre-registered falsification condition).
- A new row exists in `research/cost_admissibility_screen.py` with break-even cost and gate headroom
  for this candidate; the screen still ends with `OVERALL: PASS` and its self-checks still pass.
- Verdict is one of: **credible candidate for further validation / exploratory signal /
  rejected-failed / blocked by data**, stated with the evidence. If the net result fails the gate or
  the post-2022 sub-sample carries nothing, record it as rejected/exploratory — do not promote and
  do not tune until it passes (trial count must be reported, and any additional variants must be
  declared as new trials).
- Shortlist, hypothesis, inventory and experiment record updated consistently with the numbers
  actually observed.

## Validation
```bash
python research/cost_admissibility_screen.py            # must end with OVERALL: PASS
python -m pytest -q                                     # must pass
python research/collect_binance_crypto_funding.py --offline --construct-path   # data still rebuilds
python -m pytest -q tests/test_binance_crypto_funding.py
```

## Scope Boundaries
- No live trading, no credentials, no new dependencies, no new services, no paid data.
- Do not modify the committed Binance/OKX raw caches or the carry path; extend the analysis around
  them. If a data defect is found, fix the collector and re-run it (checksum-verified) and record it.
- Do not change the scoring of any other shortlist row, and do not re-rank the shortlist.
- Do not add more data sources or instruments to this candidate (no third exchange, no options,
  no borrow data) — keep the trial count small and declared.
- No new workflows, agents, schedules or infrastructure.
- Temporary diagnostics go under `.kilo/supervisor-reports/`; research artifacts go under
  `research/`.

## Handoff
- **Changed (Cycle 889):** added `research/collect_binance_crypto_funding.py` (checksum-verified
  Binance archive collector + `build_carry_path`), 6 raw + 2 processed crypto parquet artifacts,
  `research/reports/binance_crypto_manifest.json`, `research/experiments/cryptofunding_002_data.md`,
  `tests/test_binance_crypto_funding.py`; updated the crypto hypothesis, the shortlist (rank 8) and
  the data inventory; added `data/raw/crypto/_cache/` to `.gitignore`.
- **Verified:** `python research/cost_admissibility_screen.py` -> `OVERALL: PASS` (50/50 checks);
  `python -m pytest -q` -> **173 passed**; new module -> 15 passed. Collection is deterministic: a
  rebuild from the cached ZIPs reproduces byte-identical parquet files (SHA-256 unchanged).
- **Unresolved:** no net-of-cost result, no walk-forward split, no bootstrap CI, no screen row for
  this candidate; the archive stops at 2026-09 (no October-2026 monthly file published yet), so the
  series lags the OKX cache by ~20 days.
- **Failed approaches (do not repeat):** the live Binance API (HTTP 451) and Bybit (HTTP 403) are
  geo-blocked from this environment; the OKX public funding-history endpoint returns only ~296
  records (~98.3 days) and cannot be paged further. The working route is the Binance **archive**,
  not the exchange APIs.
