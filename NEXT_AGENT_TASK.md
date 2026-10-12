# Next Agent Task: Cycle 9 - Paper-Trading Go/No-Go Evaluation & Drift Enhancement

## Context

Cycle 8 successfully built and verified the paper-trading (prospective) validation framework. All verification checks passed:

- `src/simulation/paper_trading.py` — Paper-trading engine with `PaperTradingConfig`, `PaperTradingState`, `run_daily_paper_update`, `generate_paper_report`
- `config/paper_trading_config.yaml` — Operational configuration (alert thresholds, go/no-go criteria, output paths)
- `research/run_cycle8.py` — Daily pipeline script (idempotent, restart-safe)
- Daily artifacts produced in `data/processed/paper_trading/`:
  - `positions_YYYYMMDD.parquet` — target weights per symbol
  - `regime_YYYYMMDD.parquet` — SPY price, regime exposure
  - `risk_state_YYYYMMDD.parquet` — vol_scale, dd_scale, drawdown, exposure
  - `daily_pnl_YYYYMMDD.parquet` — mark-to-market P&L
- `research/reports/paper_trading_rolling.md` — Rolling report with Current State, Positions Table, Drift Monitoring, Performance Tracking
- State persisted in `data/processed/paper_trading_state.yaml` for restart capability

**Candidate Status**: The SPY trend-filter candidate (226-day TSMOM + combined risk overlay + SPY 200-day SMA regime filter) is now running in prospective paper-trading mode. After 63+ days (3 months), go/no-go criteria can be evaluated.

---

## Objective

Build a **go/no-go evaluation framework** that:
1. Implements automated evaluation of paper-trading track record against go/no-go criteria
2. Enhances drift monitoring with statistical tests (parameter stability, regime persistence)
3. Adds comparison against backtest baseline (Cycle 5/6 verified metrics)
4. Produces a formal go/no-go recommendation artifact

This is **NOT live trading** — it is an evaluation layer on top of the paper-trading framework.

---

## Acceptance Criteria

The Cycle 9 work must produce:

### 1. `src/simulation/evaluation.py` — Go/No-Go Evaluation Module

A new module with:
- `GoNoGoConfig` dataclass: evaluation parameters (min_days, target_sharpe, max_dd, statistical confidence)
- `GoNoGoResult` dataclass: evaluation outcome (decision, metrics, confidence intervals, rationale)
- `evaluate_go_no_go(state: PaperTradingState, config: PaperTradingConfig, backtest_baseline: dict) -> GoNoGoResult`
  - Computes rolling 63-day Sharpe, max DD, trade count from `state.cumulative_returns`
  - Compares paper Sharpe vs. backtest Sharpe (1.4178) with statistical test
  - Checks regime stability (no unexpected flips)
  - Checks risk overlay parameter stability (vol_scale, dd_scale within historical ranges)
  - Checks signal turnover vs. backtest distribution
  - Returns `decision: "GO" | "NO-GO" | "INCONCLUSIVE"` with rationale
- `generate_evaluation_report(result: GoNoGoResult, config: GoNoGoConfig) -> str` — Markdown evaluation report

### 2. `research/run_cycle9.py` — Go/No-Go Evaluation Pipeline

Script that:
- Loads frozen candidate config from `config/simulation_candidate_001.yaml`
- Loads paper-trading state from `data/processed/paper_trading_state.yaml`
- Loads backtest baseline metrics from Cycle 7 verification (hardcoded or loaded from report)
- Runs `evaluate_go_no_go`
- Exports evaluation artifact to `research/reports/go_no_go_evaluation_001.md`
- Prints decision and key metrics to console

### 3. `research/reports/go_no_go_evaluation_001.md` — Go/No-Go Evaluation Report

Living document with:
- **Header**: candidate ID, config hash, evaluation date, paper track record length
- **Backtest Baseline**: documented Cycle 5/6 metrics (Sharpe, max DD, trades, turnover, etc.)
- **Paper Performance**: rolling 63-day Sharpe, total return, max DD, trade count, annualized turnover
- **Statistical Comparison**: paper vs. backtest Sharpe with confidence interval, p-value
- **Drift Assessment**: regime stability, risk parameter stability, turnover distribution comparison
- **Decision**: GO / NO-GO / INCONCLUSIVE with explicit rationale
- **Conditions for Re-evaluation**: what would change the decision

### 4. Enhanced Drift Monitoring in `src/simulation/paper_trading.py`

Add to `run_daily_paper_update`:
- Rolling 63-day Sharpe calculation in state
- Rolling max DD in state
- Regime persistence counter (days since last flip)
- Signal turnover distribution tracking (rolling median, p95)
- Risk parameter bounds tracking (historical min/max of vol_scale, dd_scale)
- Drift alert for: rolling Sharpe < 0.5, regime persistence < 5 days after flip, vol_scale > 2.5, dd_scale < 0.2

---

## Implementation Notes

### Reuse Existing Infrastructure

- `src/simulation/paper_trading.PaperTradingState` — paper-trading state
- `src/simulation/paper_trading.PaperTradingConfig` — paper-trading config
- `src/evaluation/statistics.py` — statistical utilities (probabilistic Sharpe, Deflated Sharpe)
- `src/evaluation/robustness.py` — parameter stability tests
- `config/paper_trading_config.yaml` — go/no-go thresholds
- Cycle 7 documented baseline: test Sharpe 1.4178, max DD -7.79%, 1196 trades

### New Files to Create

- `src/simulation/evaluation.py`
- `research/run_cycle9.py`
- `research/reports/go_no_go_evaluation_001.md` (created on first run)

### Statistical Approach

- Use block-bootstrap for confidence intervals (account for autocorrelation)
- Probabilistic Sharpe Ratio (PSR) vs. backtest Sharpe
- Deflated Sharpe Ratio for multiple testing control
- Minimum track record: 63 days (configurable)
- Decision threshold: PSR > 0.95 for GO, PSR < 0.5 for NO-GO, else INCONCLUSIVE

---

## Scope Boundaries

- **In scope**: Go/no-go evaluation logic, statistical comparison, enhanced drift monitoring, evaluation report
- **Do NOT** place live trades or connect to broker APIs
- **Do NOT** add new data dependencies beyond Yahoo Finance
- **Do NOT** modify existing simulation/backtest modules (engine.py, run_cycle5-7.py)
- **Do** preserve all Cycle 1-8 artifacts

---

## Validation Commands

```bash
# Run Cycle 9 go/no-go evaluation
python3 research/run_cycle9.py

# Verify evaluation report created
test -f research/reports/go_no_go_evaluation_001.md

# Verify report has expected sections
grep -q "Backtest Baseline" research/reports/go_no_go_evaluation_001.md
grep -q "Paper Performance" research/reports/go_no_go_evaluation_001.md
grep -q "Statistical Comparison" research/reports/go_no_go_evaluation_001.md
grep -q "Drift Assessment" research/reports/go_no_go_evaluation_001.md
grep -q "Decision" research/reports/go_no_go_evaluation_001.md

# Lint
python3 -m ruff check research/run_cycle9.py src/simulation/evaluation.py src/simulation/paper_trading.py

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle9.py').read())"
python3 -c "import ast; ast.parse(open('src/simulation/evaluation.py').read())"
python3 -c "import ast; ast.parse(open('src/simulation/paper_trading.py').read())"

# Verify prior cycles still run
python3 research/run_cycle5.py 2>&1 | tail -1
python3 research/run_cycle6.py 2>&1 | tail -1
python3 research/run_cycle7.py 2>&1 | tail -3
python3 research/run_cycle8.py 2>&1 | tail -3
```

---

## Expected Outcome

- Go/no-go evaluation runs without errors on current paper-trading state
- Evaluation report produced with all required sections
- Decision is INCONCLUSIVE (since < 63 days of paper track record)
- Enhanced drift monitoring active in paper-trading engine
- Framework ready for automatic evaluation once 63+ days accumulated
- All prior cycles (1-8) continue to pass

---

## Evidence Reference

- Cycle 7 verification: all checks PASS, zero diff vs. backtest
- Cycle 6 walk-forward: mean OOS Sharpe 0.9473, 91.7% positive folds, 6013 trades
- Cycle 6 plateau: 6/6 SMA windows (150, 175, 200, 226, 250, 277) achieve Sharpe >= 0.9
- Cycle 5 promotion gate: SPY trend filter test Sharpe 1.4178, max DD -7.79%, 1196 trades
- Cycle 8: Paper-trading engine operational, daily artifacts produced, state persisted

---