# Exploratory Candidates Summary (Cycles 25-28)

## Overview
Evaluated top unblocked exploratory candidates from opportunity shortlist. All tested candidates failed primary promotion gate (WF mean OOS Sharpe >= 0.9) despite positive fold rates and adequate trade counts.

## Tested Candidates

### C3: csmomentum_001 — Long-only cross-sectional momentum (18-ETF universe)
- Hypothesis: research/hypotheses/csmomentum_001.md (v001), Config: config/csmomentum_001.yaml
- Cycle 25 execution (experiment: research/experiments/csmomentum_001_experiment_001.md)
- Test Sharpe (2018-2026): 0.5652
- WF (10yr/1yr/6mo, purge 21d/embargo 21d): 46 folds, mean OOS Sharpe 0.6619, median 0.7138, pos folds 78.3% (36/46), pooled trades 2855
- DSR (N=27): -0.1358, prob 0.4460
- Gates: WF mean>=0.9 FAIL; pos>=50% PASS; pooled>100 PASS
- Verdict: FALSIFIED/REJECTED

### C4: sectorrotation_002 — Sector rotation (9 GICS sector ETFs)
- Hypothesis: research/hypotheses/sectorrotation_002.md (v002), Config: config/sectorrotation_002.yaml
- Cycle 27 execution (experiment: research/experiments/sectorrotation_002_experiment_001.md)
- Test Sharpe (2018-2026): 0.4906
- WF: 34 folds, mean OOS Sharpe 0.6627, median 0.6559, pos folds 79.4% (27/34), pooled trades 1236
- DSR (N=18): -0.1683, prob 0.4332
- Gates: WF mean>=0.9 FAIL; pos>=50% PASS; pooled>100 PASS
- Verdict: FALSIFIED/REJECTED

### C6: macroregime_001 — Macro regime overlay extension (VIX gate on incumbent base)
- Hypothesis: research/hypotheses/macroregime_001.md (v001), Config: config/macroregime_candidate_001.yaml
- Prior full execution documented (experiment: research/experiments/macroregime_baseline_wf_001.md); Cycle 28 recorded outcome
- Test Sharpe (baseline): 0.2950; WF mean OOS Sharpe 0.4331, 24 folds, 75% pos folds, pooled 137 trades
- DSR (N=12): -0.5061, prob 0.3064
- Gates: WF mean>=0.9 FAIL; pos>=50% PASS; pooled>100 PASS
- Verdict: FALSIFIED/REJECTED

## Other Candidates (from shortlist)
- C1 (TSMOM incumbent): Credible candidate (passed WF gate in prior cycles; deployment dossier prepared). Remains in paper-trading validation track.
- C2 (long-only cross-sectional broad 18-ETF) — evaluated as C3 above (rejected)
- C5 (TSMOM parameter variants): Rejected per shortlist
- C7 (Commodity/rate futures basis/roll): Blocked by data (no futures history cached)
- C8 (Crypto perpetual funding carry): Blocked by data (no crypto/perp/funding cached)
- C9 (Volatility risk premium): Blocked by data (no tradeable vol instruments; only ^VIX index cached)
- C10 (Intraday session/time-of-day): Blocked/rejected (no intraday history cached)

## Conclusion
All unblocked exploratory candidates with sufficient cached data to support valid offline testing (C3, C4, C6) were evaluated under pre-registered, hypothesis-first conditions with honest accounting (3bps costs) and multiple-testing controls. None cleared the primary promotion gate (WF mean OOS Sharpe >= 0.9). The incumbent TSMOM (C1) remains the only candidate that has met promotion criteria. Remaining exploratory candidates on the shortlist are either blocked by data availability or already rejected.
