# Experiment: macroregime_001 — Macro Regime Overlay Extension (Baseline)

## Metadata
- Hypothesis: research/hypotheses/macroregime_001.md (v001, 2026-10-13)
- Frozen config: config/macroregime_candidate_001.yaml
- Execution: Cycle 28
- Evidence basis: Prior experiment macroregime_baseline_wf_001.md documents full execution with WF mean OOS Sharpe 0.4331, test Sharpe 0.2950, 24 folds, pooled 137 trades, DSR -0.5061 at N=12. Pre-registered falsification met.

## Baseline (from frozen config)
- TSMOM: lookback 226, skip 21, top_fraction 0.5
- Overlays: vol-target 10% (63d), DD control 15%/50% reduction
- SPY SMA 200d (base regime)
- VIX gate: threshold 30, exposure 0.5 when VIX>30, lag 1
- Universe: 7 ETFs (SPY,QQQ,IWM,TLT,GLD,EFA,EEM), regime driver ^VIX
- Costs 3bps round-trip

## Key Results (from documented execution)
- Test period 2018-01-01 to 2026-10-09: baseline test Sharpe 0.2950
- WF (10yr train / 12mo test / 6mo step, purge 21d, embargo 21d): 24 folds
- Mean OOS Sharpe: 0.4331
- Median OOS Sharpe: 0.4950
- % Positive folds: 75.0%
- Pooled OOS trades: 137
- Mean test ann return: 6.30%, mean test max DD: -9.08%
- Multiple testing (N=12): DSR -0.5061, DSR prob 0.3064; PSR vs 0.9 gate 0.0255

## Benchmarks
- Incumbent control (vix_exposure=1.0, effectively no VIX trim beyond base): test Sharpe 0.3371
- 1/N equal-weight 7-ETF (test, same period): see original experiment; control arm shows baseline underperforms vs no-VIX-trim control in that configuration

## Promotion Gates
1. WF mean OOS Sharpe >= 0.9? 0.4331 → FAIL
2. Positive fold rate >= 50%? 75.0% → PASS
3. Pooled OOS trades > 100? 137 → PASS

Falsification condition met → hypothesis FALSIFIED (Rejected/Failed).

## Verdict
Rejected/Failed. Adding VIX regime gate (threshold 30, exposure 50%) on top of already-gated incumbent does not improve performance; WF mean OOS Sharpe 0.4331 is well below 0.9 gate. DSR confirms no statistical significance after multiple testing.

## Next Steps
Do not promote. Move to next candidate from shortlist - C7? Shortlist shows C7 "Commodity/rate futures basis..." blocked by data; C8 crypto funding blocked; C9 vol risk premium blocked; C10 intraday rejected. Remaining exploratory candidates include macro regime extensions with different specifications? Or perhaps consider different approach - but many blocked. Alternatively, return to shortlist and pick best remaining unblocked exploratory (C6 was macro overlay - already tested/rejected). Next viable unblocked exploratory: C4 done (rejected), C3 done (rejected), C6 done (rejected). Others blocked. Suggest focusing on improving existing credible candidate (TSMOM incumbent) or document end of viable untested unblocked candidates per current data inventory.
