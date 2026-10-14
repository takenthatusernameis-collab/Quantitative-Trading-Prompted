# Next Agent Task: Microcap mom121 — Data Acquisition Decision (Bounded)

## Context

The microcap 12–1 momentum hypothesis (`mom121_microcap_001`) is **BLOCKED by data/infrastructure**. The previous cycle completed:

- **Free data survey:** yfinance 1.7.0 cannot provide point-in-time market cap screening or delisting events for microcaps; `get_shares_full()` enables approximate market cap = shares × price for liquid names only. Other free data sources (ccxt, fredapi, sec-edgar-downloader, pandas-datareader, quandl, finnhub, alpha_vantage, polygon, sec_api, nasdaq) are **not installed**.
- **Exploratory diagnostic:** Ran a clearly-labelled exploratory diagnostic comparing daily (existing code: 252/21) vs monthly calendar-month-end conventions on a survivorship-biased current-ETF basket. Code mechanics verified; the two conventions differ materially. Added defensive NA-handling to `src/features/momentum.py` (smallest sufficient change; no logic change to signal definition).
- **Artifacts created:** `research/experiments/mom121_microcap_001_exploratory.md` with full disclosures, survey, and ranked data source shortlist.

Full details: `research/experiments/mom121_microcap_001.md` (Section A) and `research/experiments/mom121_microcap_001_exploratory.md`.

## Objective

Make an **evidence-based decision** on how to proceed with mom121_microcap_001 given the data blocker. This is a bounded decision/planning task (no confirmatory backtest). Choose exactly one path and prepare a concrete next task.

## Acceptance criteria

1. **Review artifacts**: Read `research/experiments/mom121_microcap_001_exploratory.md`, `research/hypotheses/mom121_microcap_001.md`, and `research/experiments/mom121_microcap_001.md`. Confirm the blocker summary is accurate.

2. **Decide among valid paths** (pick exactly one):

   - **Path A (confirmatory with proper data):** Identify a specific, concrete plan to obtain point-in-time microcap data with historical market cap, shares, delistings, and point-in-time universe (e.g., CRSP/Compustat access, specific API with point-in-time semantics). Document what’s needed, realistic effort, and whether it’s feasible in this environment. **Do not** actually acquire paid data or add credentials.
   - **Path B (free approximation with strict labeling):** Define the minimal, auditable rules for constructing a free approximation using yfinance (e.g., which tickers, how to get shares history, delisting detection heuristics, survivorship caveats, minimum liquidity filters, date coverage). Explicitly state why this **cannot** be confirmatory and what disclosures are required. Only consider if it can be done without adding heavy dependencies.
   - **Path C (pivot):** Pivot to another hypothesis from `research/hypotheses/` that can run with **existing** data in `data/raw/` (ETFs/indices only) while respecting AGENTS.md discipline (hypothesis-first, baseline before complexity, honest accounting). Justify why this is higher value than waiting on microcap data.

3. **Update hypothesis status**: If choosing Path A or B, update `research/hypotheses/mom121_microcap_001.md` status/version history to reflect the decision (still blocked for confirmatory unless Path B becomes viable with ironclad disclosures). If choosing Path C, document the pivot rationale in the chosen hypothesis or in experiment notes.

4. **Write next bounded task**: Create **exactly one** new NEXT_AGENT_TASK.md with:
   - Context (including evidence)
   - Objective (single, concrete goal)
   - Acceptance criteria (testable, minimal)
   - Validation commands (exact)
   - Scope boundaries (explicitly exclude confirmatory claims if using imperfect data)

5. **Minimal verification**: Run existing tests to ensure nothing is broken.
   ```bash
   python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
   ```

## Scope boundaries

- **No paid data acquisition, no credentials, no new paid dependencies.**
- **No confirmatory microcap backtest** unless Path A is realistically feasible with resources available in this environment (and even then, only with proper point-in-time data). If not feasible, do not run one.
- **Smallest change principle.** Only make minimal doc/code edits needed to enact the decision.
- **Research/backtesting only.** No live trading.
- **Preserve evidence.** Do not downplay the data blocker or fabricate data availability.

## Validation commands

```bash
# 1. Verify artifacts exist
ls -la research/experiments/mom121_microcap_001_exploratory.md research/hypotheses/mom121_microcap_001.md

# 2. Run existing tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Completion standard

Return a concise evidence-backed decision (A, B, or C with rationale), the updated artifacts, and the new single NEXT_AGENT_TASK.md ready for the next agent.
