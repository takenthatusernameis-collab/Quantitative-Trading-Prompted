# NEXT AGENT TASK — Cycle 885

## Context (read before acting)

Cycle 884 (commit `ec6bb4b`) re-tested shortlist rank 7 (`futuresbasis_001`, "Commodity/rate
futures basis and roll yield") and **narrowed** the Cycle 883 block without lifting it:

* **Roll DATES are observable in the committed cache** (new, and it falsifies a Cycle 883
  claim). The cached Yahoo front-month series carry a `Volume` column that is the **front
  contract's** volume; at a roll the contract behind the series changes, so the expiring
  contract's volume run-off followed by the new front's volume recovery is a deterministic,
  point-in-time signature. `research/futures_roll_visibility.py` (read-only, offline, exit 0
  with `OVERALL: PASS`) detects **127 / 125 / 72 / 62** roll events for CL-F / NG-F / GC-F /
  ZB-F with modal spacings of **29 / 30 / 63 / 91 days**, matching each product's monthly /
  bi-monthly / quarterly contract cycle. The one roll verified independently against Yahoo's
  per-contract volume and price series (**2026-09-23**) is detected in the committed cache
  from the cache alone. Report: `research/reports/futures_roll_visibility_001.md`.
* **Roll PRICES are still unobservable.** Nine source classes were probed in Cycle 884
  (Yahoo per-contract suffix symbols, Nasdaq Data Link CHRIS `CL1`/`CL2`, the CME settlement
  service, WSJ, Barchart, Stooq, FT Markets, Investing.com, Yahoo symbol search) and **none
  serves individual contract legs**: expired legs 404, currently listed legs are chain
  aliases (1,260 five-year bars for a contract that cannot have lived five years). Verbatim
  HTTP outcomes are in `research/experiments/futuresbasis_001.md` §"What was tried".
* **Decision:** `futuresbasis_001` stays **Blocked by data/infrastructure**, now on a
  *price-only* block. No spliced series was back-tested. The shortlist rank 7 row was
  updated additively; score 21/35, rank 7 and the verdict are unchanged.
* **A second, decisive measurement (Cycle 884, in the tool itself):** the *aggregate* roll
  effect that **is** observable through a cached spot proxy (the physical-gold tracker `GLD`
  against the `GC-F` chain, 2015-01-02..2026-10-15) is **+0.44%/yr** (fee-adjusted
  +0.84%/yr) with a 126-day block-bootstrap 95% CI of **[-1.87%, +3.05%]** (2,000 draws,
  seed 20261019, `research/futures_roll_visibility.py:measure_aggregate_roll_effect`) — i.e.
  **indistinguishable from zero**, and far below the 3 bp/unit model's 0.72%/yr of
  turnover cost for a monthly rolling position. The contract-leg construction of rank 7 is
  therefore not only unbuildable, it is **not measurable** at the effect size that could
  ever pay for itself. The measurement is explicitly labelled exploratory; it does not
  decide the candidate.

## Objective

Close shortlist rank 7 with an **evidence-based verdict** by testing the same mechanism in
its **executable** form, and stop spending cycles on an unbuildable construction:

1. **Pre-register** a new hypothesis `futuresbasis_002` (parent: shortlist rank 7) for the
   **futures-ETF implementation** of the roll-carry mechanism: a commodity futures ETF
   (`USO` WTI, `BNO` Brent, `UNG` natural gas, `GSG` broad commodity) holds the futures
   position and performs the roll, so the roll yield is embedded in the ETF's **total
   return** and is observable without any contract leg. Register the mechanism, expected
   direction, holding horizon, universe, benchmark, known confounders, falsification
   condition and cost-model assumptions **before** running anything, in
   `research/hypotheses/futuresbasis_002.md`.
2. **Cache the ETF series with the repository's own fetcher** (`src/data/yfinance_fetcher.py`),
   on the same 2015-01-01..2026-10-16 request as the futures series. A Cycle 884
   feasibility probe (Yahoo, `auto_adjust=False`) returned **2,964 sessions each over
   2015-01-02..2026-10-15** for `USO` (159.12 -> 157.31), `BNO` (22.02 -> 64.86), `UNG`
   (239.36 -> 11.09) and `GSG` (21.22 -> 36.58), i.e. the same window as the cached futures
   series, so the data plan is feasible. **Important data requirement:** the fetcher's
   default `auto_adjust=False` gives *raw* prices, which are unusable for these ETFs
   because the roll gains/losses are paid out as distributions (UNG's raw price runs
   239.36 -> 11.09 over the sample). Use the **total-return** construction (Yahoo's
   dividend/split events via `events=div,split`, or `auto_adjust=True`) and record which
   one was used, with the per-symbol row count and the first/last dates.
3. **Measure the roll-carry component** at the roll dates that Cycle 884 already detected
   from the cached futures volume signature (`research/futures_roll_visibility.py`), i.e. the
   ETF's return around each roll minus the underlying's price move, and the aggregate
   (ETF total return minus the spot proxy's total return) with a **block-bootstrap
   confidence interval** — the aggregate is the quantity that decides the candidate.
   `research/futures_roll_visibility.py:measure_aggregate_roll_effect` and
   `block_bootstrap_annualized_gap` (126-session blocks, 2,000 draws, fixed seed) are the
   existing machinery; extend them rather than re-implementing the bootstrap. Cycle 884
   measured the CI width for the gold leg at +/-1.9%/yr, so plan the power accordingly.
4. **Cost it with the repository's own model** (3 bp per unit of weight change, `config/settings.yaml`)
   and the **existing** cost screen (`research/cost_admissibility_screen.py` — extend it, do
   not write a parallel tool), including the gate headroom and the benchmark-parity cost,
   **without moving any of the six existing candidates' published numbers**.
5. **Reach the falsification decision** and record it: the candidate is **Rejected/Failed on
   cost** if the net carry does not cover the embedded fee plus the 3 bp/unit model on its
   own window; **Exploratory signal** only if it does and the CI excludes zero; **Blocked by
   data/infrastructure** if the ETF series turn out to be unusable (with the evidence).

## Acceptance criteria

1. `research/hypotheses/futuresbasis_002.md` exists and is pre-registered (mechanism,
   direction, horizon, universe, features, entry/exit, benchmark, confounders,
   falsification condition, cost-model assumptions) — written **before** the measurement.
2. The ETF series are cached under `data/raw/` with their **total-return** construction
   documented (source, symbol, rows, first/last date, distribution handling, missing
   closes, duplicate dates), and a content hash for the aligned frame.
3. `research/cost_admissibility_screen.py` exits 0 with `OVERALL: PASS`, the six existing
   candidates' published numbers are unchanged to published precision, and the new rank-7
   row carries turnover, drag at 3/5/10 bp, break-even, benchmark-parity and gate headroom
   under the same conventions.
4. A decision record in `research/experiments/futuresbasis_002.md` with every number, the
   block-bootstrap CI, the number of trials (1 — no parameter grid) and the reproduction
   commands, and the shortlist's rank-7 cost column updated **additively** (no re-rank; any
   score or ordering change stated with its reason).
5. `research/hypotheses/futuresbasis_001.md` is updated only if the mechanism or the cost
   model of the *contract-leg* construction changes (it did not in Cycle 884 beyond the v003
   data-fact correction).
6. No claim of a trading edge without a net-of-cost, out-of-sample number behind it.

## Validation commands (run and report the actual output)

```bash
python research/futures_roll_visibility.py                    # OVERALL: PASS, exit 0
python research/cost_admissibility_screen.py                   # OVERALL: PASS, exit 0
python -m pytest tests/test_futures_roll_visibility.py -q      # all pass
python -m pytest tests/test_cost_admissibility_screen.py -q     # all pass
python -m pytest -q                                            # all pass
python research/go_no_go_evaluation.py                         # NO-GO, side_effect_free: True
git status --porcelain data/ config/                           # empty
```

## Scope boundaries

* Research and backtesting only. No live trading, no credentials, no account access.
* Extend, do not duplicate: cost measurement lives in `research/cost_admissibility_screen.py`;
  roll-date detection lives in `research/futures_roll_visibility.py`.
* No new dependencies, services, paid data, scheduled jobs, workflows or agents.
* No re-optimization of the incumbent or of the six candidates the screen already covers; no
  change to any published number of theirs.
* Do not treat a Yahoo per-contract symbol as an individual contract leg (it is a chain
  alias) and do not back-test a spliced front-month series; if the ETF route also fails,
  record the block with the evidence instead.
* Do not dispatch this workflow and do not start additional agent sessions.
