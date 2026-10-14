# Next Agent Task: Verify drift flag detection logic against full data (Bounded)

## Context

The drift analysis for the paper trading state has been updated through 2026-10-14. The `low_rolling_sharpe` drift flag is currently triggered (0.1133 < 0.5) in `data/processed/paper_trading_state.yaml`. While the analysis concludes the flag is market-driven, we have not independently verified that the drift flag detection logic (threshold, window size, calculation method) is correctly implemented and applied to the full synchronized dataset.

## Objective

Audit and verify the drift flag detection logic in the codebase to ensure it correctly computes rolling Sharpe (63d) with the same method as documented, uses the right threshold (0.5), and correctly sets the `low_rolling_sharpe` flag for the current state. This is a verification task only - no strategy changes.

## Acceptance Criteria

1. **Locate detection logic**: Identify where `low_rolling_sharpe` flag is computed/set (search for "low_rolling_sharpe", "rolling_sharpe", "drift_flags", etc.).
2. **Verify calculation**: Reproduce the rolling Sharpe (63d) calculation from code logic against the full daily P&L series (447 days through 2026-10-14) and confirm it matches the stored value (0.1133) and our computed value (~0.114).
3. **Document findings**: Create `research/reports/drift_flag_verification_001.md` summarizing:
   - Location of detection logic (file:line)
   - Calculation formula (e.g., annualized Sharpe with sqrt(252), mean/std over window, how NaN handled)
   - Window size, threshold, lookback
   - Comparison: code-computed vs stored vs independently computed
   - Confirmation of correctness or any discrepancies found
4. **No modifications**: Do not change detection logic, thresholds, or state unless a clear bug is found. If a bug is found, document it precisely and do not fix it as part of this task (create a separate fix task).
5. **Run tests**: Execute `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` to ensure no regressions.

## Validation Commands

```bash
# Find detection logic
grep -rn "low_rolling_sharpe\|rolling_sharpe_63d" src | head -20

# Verify against state
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    s = yaml.safe_load(f)
print(s['rolling_sharpe_63d'], s['drift_flags'])
"

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Read-only verification.** Do not modify code or state.
- **Focused scope.** Only audit the drift flag detection logic.
- **Evidence-based.** If discrepancy found, document exact values and file locations.
- Do not commit unless explicitly requested.

## Completion Standard

- Detection logic located and documented with file paths/line numbers.
- Independent reproduction matches stored values.
- Verification report written with clear conclusion.
- Tests passing.
- No unintended modifications to codebase.

(End of file)
