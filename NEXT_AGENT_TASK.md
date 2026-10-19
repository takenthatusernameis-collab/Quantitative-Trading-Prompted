# NEXT AGENT TASK — Cycle 883

## Context (read before acting)

Cycle 882 completed the cost column of `research/reports/opportunity_shortlist.md` for **every**
row and added the **gate headroom** to `research/cost_admissibility_screen.py`. The evidence it
produced (all in `research/reports/cost_admissibility_screen_001.md` and
`research/experiments/cost_admissibility_screen_001.md`):

* `csmomentum_001`, `sectorrotation_001` and `macroregime_001` are all **ADMISSIBLE** on cost
  (gross signal 62x–141x what their own turnover requires) but all three are **below** the
  repository's 0.9 walk-forward gate before a basis point is charged (canonical walk-forward mean
  OOS Sharpe 0.8458 / 0.8529 / 0.4733), their **gate headroom is negative**
  (-30.10 / -25.31 bp/unit, and *no crossing at all* for `macroregime_001`) and their
  benchmark-parity cost is negative (-5.33 / -31.16 / -86.15 bp/unit). Their headroom is
  **survival, not edge**; they stay **Rejected/Failed** on their own pre-registered gates.
* The shortlist's four remaining rows have **no derivable cost basis**:
  rank 5 (TSMOM parameter variants — already rejected on the repository's own 100-configuration
  grid, no separate candidate configuration exists to cost),
  rank 7 (commodity/rate futures basis and roll yield — **no futures series is cached**),
  rank 8 (crypto perpetual funding-rate carry — no crypto or funding series is cached),
  rank 9 (volatility risk premium — no *tradeable* volatility instrument is cached; `^VIX` is an
  index, not an executable return series).
* Per `AGENTS.md`'s priority order, **data readiness and integrity comes first**, and rank 7 is
  the only blocked row that has (i) a plausible, documented structural mechanism (basis
  compensation, roll yield, forced flows), (ii) a free, already-supported data source, and
  (iii) a low-friction execution story. Ranks 8 and 9 need a venue/broker/borrow stack the
  repository's automation cannot execute, so they stay parked (see the scope boundaries).

## Objective

Bring **shortlist rank 7 (commodity/rate futures basis and roll yield)** to a state where it can
be **costed**, or close the row with evidence.

1. **Data readiness (hard gate).** Cache the front-month futures series the repository does not
   have yet, with an **explicit, documented, point-in-time roll rule**, and publish a data
   integrity record: coverage, gaps, duplicate dates, the roll dates detected in the data, the
   roll transaction cost that the construction actually pays, and the content hash of the aligned
   frame. The known trap that must be addressed explicitly: a backtest on a *spliced* front-month
   series silently embeds the roll at an unobservable price and therefore **understates the roll
   cost and misstates the roll yield** — the construction must either pay the roll or state
   plainly that it cannot.
2. **A transparent baseline, then its cost.** Build the simplest possible baseline for the
   mechanism (no parameter search, no optimisation, no ensemble, no ML) and measure it with the
   repository's own screen machinery — **extend `research/cost_admissibility_screen.py`, do not
   create a parallel tool** — including the **gate headroom** and the benchmark-parity cost.
3. **A falsification decision.** If the roll-adjusted baseline cannot cover the roll cost plus
   the repository's 3 bp/unit model on its own window, the candidate is **Rejected/Failed on
   cost**, and the record says so with the numbers. A negative result that is recorded is a
   successful cycle.

## Acceptance criteria

1. **A hypothesis document exists** at `research/hypotheses/futuresbasis_001.md` with every
   element `AGENTS.md` requires: mechanism, expected direction and magnitude, holding horizon,
   asset universe, features and data sources, entry/exit rules, benchmark, known confounders,
   **falsification condition**, and cost-model assumptions.
2. **A committed cache and an integrity record** for the futures series actually used, including
   the roll rule, the roll dates, the roll cost paid, the coverage/gap/duplicate counts and the
   aligned frame's content hash. The record states plainly whether a *point-in-time* roll can be
   constructed from what is available; if it cannot, the cycle ends with a **"blocked by data"**
   record and the next task resolves the block — it does **not** quietly back-test a spliced
   series.
3. **The screen measures the candidate** with the same machinery and the same conventions as the
   other five candidates: annualized turnover, drag at 3/5/10 bp/unit, net annualized return,
   break-even cost, benchmark-parity cost, **gate headroom** (canonical scale, threshold named),
   and the **same-fold** benchmark. The screen's existing published numbers for the six candidates
   it already covers must not move.
4. **The candidate's own published record is reproduced from the cache** with a stated tolerance
   rule (the unit of the last published decimal; counts exact), in the same style as the screen's
   existing reproduction tables.
5. **A decision label** — "Credible candidate for further validation" / "Exploratory signal" /
   "Rejected/failed" / "Blocked by data/infrastructure" — with the numbers behind it, written into
   `research/experiments/` and into the shortlist's cost column (additively).
6. **The shortlist is not silently re-ranked.** Any change to a row's score or ordering must be
   stated with its reason in the report.

## Validation commands (all must be run and reported with their actual output)

```bash
python research/cost_admissibility_screen.py                 # OVERALL: PASS, exit 0
python -m pytest tests/test_cost_admissibility_screen.py -q   # all pass
python -m pytest -q                                           # all pass
python research/go_no_go_evaluation.py                        # NO-GO, side_effect_free: True
git status --porcelain data/ config/                          # empty
```

## Scope boundaries

* **Research and backtesting only.** No live trading, no orders, no credentials, no account
  access. No changes to the live paper-trading state, the promotion gates, the cost model or the
  frozen candidate configurations.
* **Extend, do not duplicate.** The cost measurement lives in
  `research/cost_admissibility_screen.py`. A new standalone screening script is out of scope.
* **No new dependencies, services, paid data, scheduled jobs, workflows or agents** unless the
  task's evidence requires it and the benefit is documented in the cycle record. The repository
  already caches Yahoo Finance data through `src/data/yfinance_fetcher.py`; reuse it.
* **Ranks 5, 8 and 9 stay as they are** (rank 5 rejected on the existing grid; ranks 8 and 9
  parked with the data reason already recorded in the shortlist). Do not start them in this cycle.
* **No re-optimization** of the incumbent or of any of the five candidates the screen already
  covers, and no change to any published number of theirs.
* Do not dispatch this workflow and do not start additional agent sessions.

## Failure and interruption handling

* If the futures data cannot be fetched, aligned or rolled honestly, **stop** and record
  "Blocked by data" with the evidence (what was tried, what failed, what would unblock it). Do
  not substitute a spliced series and call it point-in-time.
* If any published number of the five existing candidates moves, that is a **FAIL to be
  reported**, never a re-tune: the screen's published block for them must stay identical to the
  published precision.
