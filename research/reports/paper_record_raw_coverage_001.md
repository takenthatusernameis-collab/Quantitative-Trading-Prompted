# Paper record vs committed raw-cache coverage

Read-only audit produced by `research/paper_record_raw_coverage_audit.py`.
No file under `data/` or `config/` is written; values are re-derived from the
committed state and cache.

## Coverage

| quantity | value |
|---|---|
| universe checked | `SPY`, `QQQ`, `IWM`, `TLT`, `GLD`, `EFA`, `EEM` |
| committed raw coverage end (min across universe) | `2026-11-10` |
| record window | `2025-01-02` .. `2026-11-18` |
| record sessions | `472` |
| sessions covered by committed raw | `466` |
| sessions **not** re-derivable from `data/raw` | `6` |

Per-symbol last committed session:

| symbol | last session |
|---|---|
| `EEM` | `2026-11-10` |
| `EFA` | `2026-11-10` |
| `GLD` | `2026-11-10` |
| `IWM` | `2026-11-10` |
| `QQQ` | `2026-11-10` |
| `SPY` | `2026-11-10` |
| `TLT` | `2026-11-10` |

Unverified record sessions:
  - 2026-11-11
  - 2026-11-12
  - 2026-11-13
  - 2026-11-16
  - 2026-11-17
  - 2026-11-18

The extension path (`research/extend_paper_trading_state.py`, Cycle 854
contract) never writes `data/raw`; it fetches into a scratch directory that is
discarded. Sessions listed above therefore rest only on the state file itself.

## Metric recurrence and decision sensitivity

| quantity | value |
|---|---|
| stored `rolling_sharpe_63d` | `-1.9744867954469325` |
| reproduced from stored returns (last 63) | `-1.9744867954469325` |
| reproduced exactly | `True` |
| covered-only `rolling_sharpe_63d` (through `2026-11-10`) | `-1.4394168982987599` |
| alert threshold | `0.5` |
| `low_rolling_sharpe` under full window | `True` |
| `low_rolling_sharpe` under covered-only window | `True` |

Interpretation: the `low_rolling_sharpe` verdict is **unchanged** under the covered-only window.

## Reproduce

```
python research/paper_record_raw_coverage_audit.py
```
