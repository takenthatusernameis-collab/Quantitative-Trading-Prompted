# Experiment: Cost gate break-even audit (cost_gate_break_even_001, Cycle 913)

## Hypothesis
- Measure cost boundary of promotion-gate statistic for tsmomentum_spytrend_001, csmomentum_001, sectorrotation_001.

## Data used
- Committed parquet cache in data/raw/ (cache-only, no fetcher/network).
- OHLC used for bid-ask floor proxy (daily (High-Low)/Close).

## Configuration
- Candidates: tsmomentum_spytrend_001, csmomentum_001, sectorrotation_001
- Gates unchanged: wf_mean>=0.9, pos_fold_rate>=0.5, pooled_trades>100
- Cost grid/bisection pre-registered; spread percentiles [10, 25, 50]

## Results
- tsmom wf_mean @3bp: 0.947307
- csmom wf_mean backtest @3bp: 0.697524
- sector wf_mean @3bp: 0.847243

## Trials
- Fixed cost grid + bisection; no parameter search.

## Reproduction commands
- python research/cost_gate_break_even_audit.py
- python -m pytest -q tests/test_cost_gate_break_even_audit.py
- python -m pytest -q
- git status --porcelain data/
- git diff --stat src/ config/ research/experiments/ research/reports/
