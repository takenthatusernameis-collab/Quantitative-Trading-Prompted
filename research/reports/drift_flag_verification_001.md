# Drift Flag Verification Report

## Location of Detection Logic
The drift flag detection logic for `low_rolling_sharpe` is located in:
- **File**: `src/simulation/paper_trading.py`
- **Lines**: 355-361

Specific code:
```python
# Enhanced drift alerts
if rolling_sharpe < 0.5 and len(returns_arr) >= 20:
    drift_flags["low_rolling_sharpe"] = {
        "value": rolling_sharpe,
        "threshold": 0.5,
        "date": latest_date,
    }
```

## Calculation Formula
The rolling Sharpe calculation is performed in lines 273-284 of `src/simulation/paper_trading.py`:

1. **Returns Array Construction**:
   ```python
   returns_arr = np.array(state.cumulative_returns + [float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0])
   ```

2. **Window Selection** (lines 274-277):
   - If `len(returns_arr) >= 63`: use last 63 returns (`recent_returns = returns_arr[-63:]`)
   - Otherwise: use all available returns

3. **Sharpe Calculation** (lines 279-284):
   - If `len(recent_returns) > 1`:
     - `recent_vol = np.std(recent_returns, ddof=1) * np.sqrt(252)` (annualized volatility)
     - `recent_ann_ret = np.mean(recent_returns) * 252` (annualized return)
     - `rolling_sharpe = recent_ann_ret / recent_vol if recent_vol > 0 else 0.0`
   - Otherwise: `rolling_sharpe = 0.0`

**Key Parameters**:
- **Window size**: 63 trading days
- **Threshold**: 0.5 (annualized Sharpe ratio)
- **Lookback**: Uses most recent 63 days of returns
- **Annualization factor**: sqrt(252) for volatility, *252 for returns
- **Degrees of freedom**: ddof=1 for standard deviation (sample std dev)

## Comparison: Code-computed vs Stored vs Independently Computed

### Data Summary
- **Total days of returns data**: 447 (2025-01-02 to 2026-10-14)
- **Sufficient data for 63-day window**: Yes (447 >= 63)

### Stored Value (from state)
```yaml
rolling_sharpe_63d: 0.11333136870186329
drift_flags:
  low_rolling_sharpe:
    value: 0.11333136870186329
    threshold: 0.5
    date: '2026-10-14'
```

### Independent Verification
Our verification script calculated:
- **Rolling 63-day Sharpe**: 0.11333136870186329
- **Annualized return** (last 63 days): 0.008986
- **Annualized volatility** (last 63 days): 0.079289
- **Sharpe ratio**: 0.11333136870186329

### Results
- **Code-computed vs Stored**: Exact match (difference < 1e-10)
- **Code-computed vs Independent**: Exact match (difference < 1e-10)
- **All three values identical**: ✓

### Manual Calculation Verification
For the last 63 days of returns:
- Mean daily return: 0.000036
- Standard deviation (sample): 0.004995
- Annualized return: 0.000036 × 252 = 0.008986
- Annualized volatility: 0.004995 × √252 = 0.079289
- Sharpe ratio: 0.008986 / 0.079289 = 0.113331

## Conclusion
The drift flag detection logic is **correctly implemented and functioning as designed**.

**Verification Summary**:
1. ✅ Detection logic located at `src/simulation/paper_trading.py:355-361`
2. ✅ Calculation formula verified: 63-day window, annualized Sharpe with sqrt(252) scaling
3. ✅ Window size: 63 days, threshold: 0.5
4. ✅ Values match: stored (0.113331) = code-computed (0.113331) = independently computed (0.113331)
5. ✅ Drift flag correctly triggered: 0.113331 < 0.5 → `low_rolling_sharpe` flag set
6. ✅ All tests pass: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` (10/10 passed)

**No discrepancies found** in the drift flag detection logic. The system is correctly identifying the low rolling Sharpe condition based on the established criteria.