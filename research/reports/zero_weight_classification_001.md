# Zero-weight position classification (2026-11-02 .. 2026-11-18)

Read-only audit produced from committed state and artifacts only. No file under
`data/` or `config/` is written; no network fetch and no gate-cycle extend is
required. Values are re-derived from the committed positions, regime, and
risk_state parquet files plus `data/processed/paper_trading_state.yaml`.

## Question

Recent positions parquet files (2026-11-09 through 2026-11-18) were suspected of
containing only zero weights while earlier files (e.g. 2025-01) carry nonzero
weights. The open question: is each zero-weight date **intended-flat** (regime
de-risked to cash, zero exposure) or a **dropped write** (positions write failed
while regime/risk state stayed nonzero)?

## Method

For each record session `2026-11-02` .. `2026-11-18`:
- read `data/processed/paper_trading/positions_YYYYMMDD.parquet`, compute
  `sum(|weight|)` and whether every weight is zero;
- read `regime_YYYYMMDD.parquet`, take `regime_exposure`;
- read `risk_state_YYYYMMDD.parquet`;
- cross-check `regime_exposure` against `run_history[-1]` for the same date in
  `paper_trading_state.yaml`.

Classification rule:
- zero weights AND zero `regime_exposure` → **intended-flat** (no defect);
- zero weights AND nonzero `regime_exposure`/risk state → **DROPPED-WRITE** (defect).

## Per-session classification

| date | positions_all_zero | sum\|weight\| | regime_exposure | run_history match | classification |
|---|---|---|---|---|---|
| 2026-11-02 | False | 0.690060 | 1.0 | YES | active (nonzero weights) |
| 2026-11-03 | False | 0.691699 | 1.0 | YES | active (nonzero weights) |
| 2026-11-04 | False | 0.681884 | 1.0 | YES | active (nonzero weights) |
| 2026-11-05 | False | 0.561076 | 1.0 | YES | active (nonzero weights) |
| 2026-11-06 | False | 0.554571 | 1.0 | YES | active (nonzero weights) |
| 2026-11-09 | False | 0.524062 | 1.0 | YES | active (nonzero weights) |
| 2026-11-10 | False | 0.526472 | 1.0 | YES | active (nonzero weights) |
| 2026-11-11 | False | 0.516949 | 1.0 | YES | active (nonzero weights) |
| 2026-11-12 | False | 0.515143 | 1.0 | YES | active (nonzero weights) |
| 2026-11-13 | False | 0.515204 | 1.0 | YES | active (nonzero weights) |
| 2026-11-16 | False | 0.509731 | 1.0 | YES | active (nonzero weights) |
| 2026-11-17 | False | 0.513206 | 1.0 | YES | active (nonzero weights) |
| 2026-11-18 | True | 0.000000 | 0.0 | YES | intended-flat (zero exposure) |

## Conclusion

No dropped-write defect. Every session with all-zero positions
(`2026-11-18`) also has `regime_exposure == 0.0`, matching the persisted state
and the documented SPY<200d SMA liquidation day
(`research/reports/drift_decision_20261118.md` §7: turnover `0.5132` on the
regime-transition liquidation day). All other recent sessions carry nonzero
weights with `regime_exposure == 1.0`.

The zero-weight premise (positions 2026-11-09 .. 2026-11-18 all zero) does not
hold: 2026-11-09 through 2026-11-17 are active; only 2026-11-18 is flat, and it
is intended.

## Reproduce

```
python3 - <<'EOF'
import pandas as pd, yaml
from pathlib import Path
PT = Path("data/processed/paper_trading")
state = yaml.safe_load(open("data/processed/paper_trading_state.yaml"))
rh = {e.get("date"): e for e in state.get("run_history", [])}
for d in ["2026-11-02","2026-11-03","2026-11-04","2026-11-05","2026-11-06",
          "2026-11-09","2026-11-10","2026-11-11","2026-11-12","2026-11-13",
          "2026-11-16","2026-11-17","2026-11-18"]:
    ds = d.replace("-", "")
    pos = pd.read_parquet(PT / f"positions_{ds}.parquet")
    reg = pd.read_parquet(PT / f"regime_{ds}.parquet")
    w = pos["weight"].astype(float)
    all_zero = bool((w == 0.0).all())
    exp = float(reg["regime_exposure"].iloc[0])
    print(d, "all_zero=", all_zero, "sum_abs_w=", float(w.abs().sum()),
          "regime_exposure=", exp, "match=", rh.get(d, {}).get("regime_exposure") == exp)
EOF
```

## Verification artifacts

- `src/simulation/paper_trading.py:490-515` writes `positions_*.parquet` and
  `regime_*.parquet` from the same `regime_exp` value, so the two artifacts are
  jointly consistent by construction.
- `research/drift_invariant_check.py` already encodes the invariant "zero
  exposure implies zero position weights" (check 3) and exits 0 on the committed
  state (`SUMMARY sessions=472 regime_transitions=7 high_turnover_sessions=7 threshold=0.5`).
