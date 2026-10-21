# Experiment: SMA-175 full promotion gate eval (tsmomentum_sma175_candidate, Cycle 920)

Read-only evaluation of SMA-175 candidate against full promotion gate suite from config/promotion_gates.yaml.

- Decision: NO-GO
- full_period_sharpe: 1.607869
- rolling_63d_sharpe: -0.448918
- max_drawdown: -0.094633
- rolling_63d_max_dd: -0.038564
- psr_normal: 0.896592
- psr_target: 1.4178
- psr_target_source: config/promotion_gates.yaml gate 'psr' (backtest Sharpe baseline 1.4178); src.simulation.evaluation.GoNoGoConfig.backtest_sharpe
- sharpe_se: 0.150565
- sharpe_backtest_scale: 1.447467
- psr_zone: grey_zone
- regime_flips: 277
- track_record_length: 8488
- failed_gates: rolling_63d_sharpe, psr
- structural_pass: True
- candidate_promotable (every promotion gate passes): False
- OVERALL: PASS (verdict on the tool's own internal checks)

## Research label (Cycle 921, AGENTS.md decision discipline)
rejected/failed

## Gate reachability (computed by research/tsmomentum_sma175_psr_reachability.py)
- Observed Sharpe: 1.607869; Sharpe SE: 0.150565
- PSR target: 1.4178
- Observed Sharpe required for psr=0.95 at that SE: 1.665458
- Gap to observed Sharpe: 0.057589
- Track-record sessions: 8488
- Additional sessions needed at observed mean/dispersion: 5923 (14411 total)
- Attainable: YES
- Second failed gate: rolling_63d_sharpe = -0.448918 vs threshold 0.9 (gap 1.348918); not addressed by sample size alone.
