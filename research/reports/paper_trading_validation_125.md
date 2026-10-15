# Paper Trading Validation Report — Cycle 125

## Timestamp Gate
- Session time (UTC): 2026-10-15T14:23:03Z
- Post-close gate: 2026-10-17T20:00:00Z
- **Gate NOT MET** (session_time < gate). No fetch or replay performed per protocol.

## Verification Results

### 1. Independent Rolling-63-Day Sharpe Recomputation
- Source: `data/processed/paper_trading_state.yaml`, last 63 `cumulative_returns`
- Formula: `(mean*252) / (std(ddof=1)*sqrt(252))`
- Computed: **0.11333136870186278**
- Stored (`drift_flags.low_rolling_sharpe.value`): **0.11333136870186329**
- Difference: **5.13e-16** (< 1e-12 threshold) — **PASS**

### 2. Regime Flip Verification
- Source: `run_history.regime_exposure` transitions
- Recomputed flips: **6**
- Stored: 6 — **PASS**

### 3. Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** — **PASS**

## Track Record (unchanged — no new data)
- Days: **447** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Sharpe: **1.9272**
- Max drawdown: **-2.93%**
- Rolling 63-day Sharpe: **0.1133**
- Regime: risk-on (132 days)

## Drift Flag
- `low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**.
- Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

## Blocker
- No fetch attempted: post-close gate (2026-10-17T20:00:00Z) not yet reached.
- Per protocol, evaluation must occur at/after this time before any data acquisition.

## Next Cycle
- Re-evaluate timestamp gate. If met, attempt post-close fetch and replay extension.