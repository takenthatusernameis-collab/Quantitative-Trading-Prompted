# VIX Backfill Evidence Artifact (vix_backfill_001)

## Gap closed
Priority 1 (data readiness and integrity): `^VIX` cache previously covered only 2025-01-02 .. 2026-10-16, blocking any regime-gated test that needs a long VIX history. Cycle 872 backfilled `data/raw/^VIX.parquet` to 2004-11-18 using the existing `yfinance` path.

## Provider and schema
- Provider: Yahoo Finance via `yfinance` (see `src/data/yfinance_fetcher.py`)
- Symbol: `^VIX` (CBOE Volatility Index; index, not tradeable)
- Schema: `Open High Low Close Volume`, daily frequency, UTC index, `auto_adjust=False`, EOD `Close`
- File: `data/raw/^VIX.parquet`

## Coverage
- Rows: 5,514
- Range: 2004-11-18 .. 2026-10-16
- Close completeness: 100.0%
- Duplicate dates: 0
- NaN `Close`: none

## Overlap integrity check (2025-01-02 .. 2026-10-16)
- Max relative diff on `Close`: 0.0
- Previously cached rows byte-identical to the newly downloaded series over the overlap
- sha256 of overlapping `Close`: `58da9ca2f088906a`
- Extension is append-only in time

## Re-audit outcome
`research/month_end_candidate_reaudit.py` now runs on the real VIX gate (no ablation):
- Legacy candidate: test Sharpe 0.2950, max drawdown -0.1807, turnover 3.13x, 58 trades; WF mean OOS Sharpe 0.4331 over 24 folds, 75.0% positive, 137 pooled trades
- Config-faithful candidate: WF mean OOS Sharpe 0.2636, positive fold rate 66.7%, 193 pooled trades
- Gate: net out-of-sample Sharpe >= 0.9
- Verdict: unchanged (Rejected/Failed); all three gates fail

Cycle 871 ablation numbers are retained as a documented alternative in `research/experiments/month_end_candidate_reaudit_001.md` ("Cycle 871 ablation alternative").

## Reproduction command
```
python research/month_end_candidate_reaudit.py
```
Expected: `OVERALL: PASS, 17/17`.

## Validation
- `python research/rebalance_schedule_audit.py` → OVERALL: PASS
- `python research/sectorrotation_long_sample_feasibility.py` → runs clean (NO-GO, unchanged)
- `python -m pytest -q` → 82 passed
- `git status --porcelain config/ data/processed/` → empty
