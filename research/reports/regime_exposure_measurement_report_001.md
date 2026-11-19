# Regime exposure convention — measurement report (both paths)

*Generated: 2026-11-19T01:57:00Z*
*Candidate: `tsmomentum_spytrend_001` (incumbent). Nothing is promoted, re-fit or re-ranked.*
*Correction context: `research/reports/deployment_dossier_001.md:279` and `research/reports/go_nogo_evaluation_001.md:75` corrected to reflect that the default path uses session t's own close (same-session), while `lag_regime_exposure=True` provides point-in-time convention.*

## Reproduction commands

All results below are produced by the committed code at HEAD `5363746` on the same cached data (`data/raw/`). No config, threshold, universe, cost model, or state was modified.

### Committed (default) path — same-session regime exposure
```bash
/tmp/kilo-venv/bin/python -c "
import sys
sys.path.insert(0, 'research')
from run_cycle6 import run_walkforward
metrics = run_walkforward(config_path='config/simulation_candidate_001.yaml')
print('Mean OOS Sharpe:', metrics['mean_oos_sharpe'])
print('Pooled trades:', metrics['pooled_trades'])
print('Folds:', metrics['n_folds'])
"
```

### Point-in-time path — lagged regime exposure (`lag_regime_exposure=True`)
```bash
/tmp/kilo-venv/bin/python -c "
import sys
sys.path.insert(0, 'research')
from run_cycle6 import run_walkforward
metrics = run_walkforward(config_path='config/simulation_candidate_001.yaml', lag_regime_exposure=True)
print('Mean OOS Sharpe:', metrics['mean_oos_sharpe'])
print('Pooled trades:', metrics['pooled_trades'])
print('Folds:', metrics['n_folds'])
"
```

### Simulation engine — whole history (1993-01-01 … 2026-11-18)
```bash
# Default path
/tmp/kilo-venv/bin/python -c "
from src.simulation.engine import run_simulation
from src.simulation.config import SimulationConfig
config = SimulationConfig.from_yaml('config/simulation_candidate_001.yaml')
result = run_simulation(config)
print('Max DD:', result.max_drawdown)
print('Total return:', result.total_return)
"

# Lagged path
/tmp/kilo-venv/bin/python -c "
from src.simulation.engine import run_simulation
from src.simulation.config import SimulationConfig
config = SimulationConfig.from_yaml('config/simulation_candidate_001.yaml')
config.lag_regime_exposure = True
result = run_simulation(config)
print('Max DD:', result.max_drawdown)
print('Total return:', result.total_return)
"
```

## Results

### Walk-forward (48 folds, 1993-01-01 … 2026-10-09)

| Convention | Mean OOS Sharpe | % positive folds | Pooled OOS trades |
|------------|-----------------|------------------|-------------------|
| Committed (same-session, `lag_regime_exposure=False`) | **0.947307** | 0.9167 | 6013 |
| Point-in-time (`lag_regime_exposure=True`) | **0.153040** | 0.7083 | 6060 |

*Default path reproduces the published anchor exactly (`research/experiments/tsmomentum_regime_filter_wf_001.md`).*

### Post-2017 test period (the period the live record is measured against)

| Convention | Sharpe | Ann. return | Max drawdown | Trades | Avg daily turnover |
|------------|--------|-------------|--------------|--------|-------------------|
| Committed (same-session) | 1.333367 | 0.138454 | -7.7940% | 1218 | 0.052496 |
| Point-in-time (shift(1)) | 0.555815 | 0.069569 | -15.4646% | 1247 | 0.052496 |

### Simulation engine — whole history (8504 sessions, 1993-01-01 … 2026-11-18)

| Convention | Max drawdown | Total return |
|------------|--------------|--------------|
| Default (`lag_regime_exposure=False`) | -9.9349% | (matches anchor) |
| Lagged (`lag_regime_exposure=True`) | -16.4972% | (lower) |

*Default path vs a frozen copy of `engine.py` with the `if config.lag_regime_exposure:` branch deleted: **daily frame byte-identical** (`check_exact=True`) and identical metrics — the switch is default-neutral.*

*Lagged exposure equals the committed rule shifted one session exactly: `exposure_committed(...).shift(1).fillna(0.0)` asserted on the real SPY series.*

### Committed live paper-trading record (472 sessions through 2026-11-18)

| Quantity | Value |
|----------|-------|
| Record sessions | 472 |
| Sessions recorded at zero exposure (regime cash-out) | 55 |
| Sessions recorded at full exposure | 411 |
| Mean base-portfolio return on cash-out sessions | 0.00053990 |
| Median base-portfolio return on cash-out sessions | 0.00113708 |
| Sum of base-portfolio returns on cash-out sessions | 0.02969435 |
| Worst / best base-portfolio return on a cash-out session | -0.04991608 / 0.08283898 |
| Cash-out sessions with a negative base return | 25 of 55 |
| Mean base-portfolio return on full-exposure sessions | 0.00082150 |

*"Base-portfolio return" = equal-weight top-half momentum portfolio from committed cache. On cash-out sessions the strategy recorded cash, so the live record's return on those sessions reflects the same-session regime decision.*

## Integrity checks

| Check | Result |
|-------|--------|
| `data/` tree digest before/after | byte-identical |
| `config/` tree digest before/after | byte-identical |
| `data/processed/paper_trading_state.yaml` sha256 | `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750` (unchanged) |
| `git status --porcelain -- data/raw` | empty |
| `pytest -q tests/test_regime_exposure_lag_switch.py tests/test_tsmomentum_regime_lookahead_audit_001.py` | 10 passed |
| `ruff check` on touched files | clean |

## Decision status

- Candidate remains **NO-GO** (`research/go_no_go_evaluation.py` → NO-GO on committed record)
- Promotion decision unchanged
- No production code, thresholds, configs, state, or committed artifacts modified
- Only documentation corrections (two reports) and this measurement report added