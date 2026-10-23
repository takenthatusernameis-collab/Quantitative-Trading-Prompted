# Experiment: SMA-175 full promotion gate eval (tsmomentum_sma175_candidate, Cycle 920)

Read-only evaluation of SMA-175 candidate against full promotion gate suite from config/promotion_gates.yaml.

- Decision: NO-GO
- full_period_sharpe: 1.607677
- rolling_63d_sharpe: -0.118932
- max_drawdown: -0.094633
- rolling_63d_max_dd: -0.038564
- psr_normal: 0.899699
- psr_target: 1.4178
- psr_target_source: config/promotion_gates.yaml gate 'psr' (backtest Sharpe baseline 1.4178); src.simulation.evaluation.GoNoGoConfig.backtest_sharpe
- sharpe_se: 0.148360
- sharpe_backtest_scale: 1.447212
- psr_zone: grey_zone
- regime_flips: 277
- track_record_length: 8490
- failed_gates: rolling_63d_sharpe, psr
- structural_pass: True
- candidate_promotable (every promotion gate passes): False
- OVERALL: PASS (verdict on the tool's own internal checks)
