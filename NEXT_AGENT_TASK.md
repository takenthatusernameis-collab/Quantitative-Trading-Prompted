# Next Agent Task: Microcap mom121 — Data Acquisition Planning (Bounded)

## Context

The microcap 12–1 momentum hypothesis (`mom121_microcap_001`) is **BLOCKED by data/infrastructure**. Previous work completed:

1. **Data gate audit:** Confirmed absence of point-in-time microcap data in repository cache and configured data sources (yfinance). Zero individual stock data files exist; yfinance lacks historical market cap, shares outstanding, and delisting data.

2. **Exploratory diagnostic:** Verified pipeline mechanics using ETF proxy (clearly labeled as exploratory, not confirmatory) - `research/experiments/mom121_microcap_001_exploratory.md`.

3. **Hypothesis status:** Updated to v0.3 documenting decision to pursue Path A (identify plan for proper data) while maintaining blocked status for confirmatory testing.

4. **Alternative hypotheses:** All ETF-based candidates from the opportunity shortlist (C3, C4, C6) have been tested and rejected/failed. TSMOM incumbent (C1) is frozen due to lack of new market data.

## Objective

Document specific, concrete requirements for point-in-time microcap data acquisition to enable future confirmatory testing of mom121_microcap_001, without acquiring data or violating constraints.

## Acceptance criteria

1. **Identify data requirements:** Specify exact data fields needed for point-in-time microcap universe construction with delisting treatment.

2. **Evaluate feasible sources:** Assess whether requirements can be met with accessible free data sources in this environment (yfinance, ccxt, etc.).

3. **Document acquisition plan:** If feasible sources exist, outline minimal acquisition steps; if not, state clearly that proper confirmatory testing requires paid/institutional data not available here.

4. **Update hypothesis status:** Maintain `research/hypotheses/mom121_microcap_001.md` status as blocked for confirmatory testing unless Path B becomes viable with ironclad disclosures (deemed not feasible).

5. **Minimal verification:** Run existing tests to ensure nothing is broken.

## Validation commands

```bash
# 1. Verify hypothesis files exist and show updated status
ls -la research/hypotheses/mom121_microcap_001.md
grep -A5 "v0.3" research/hypotheses/mom121_microcap_001.md

# 2. Run existing tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope boundaries

- **No paid data acquisition, no credentials, no new paid dependencies.**
- **No confirmatory microcap backtest** - hypothesis remains blocked for confirmatory testing.
- **No actual data fetching** - pure documentation/planning task.
- **Research/backtesting only.** No live trading.
- **Preserve evidence.** Do not downplay data blocker or fabricate data availability.

## Completion standard

Return a concise evidence-backed decision documenting requirements for point-in-time microcap data, confirmation that no feasible free sources exist in this environment, and the updated hypothesis status ready for the next agent.