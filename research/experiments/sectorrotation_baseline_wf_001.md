# Experiment: Corrected C4 Sector-Rotation Evaluation

> **Final status: Rejected/Failed under the frozen promotion rule.** This record supersedes the prior Cycle 15 report. The prior report is preserved as `research/experiments/sectorrotation_baseline_wf_001_pre-correction.md`; its 18-ETF / 48-fold results were the defective historical execution and must not be used as C4 evidence.

## Reproducible execution

- **Workflow run:** [Cycle 15 C4 cache-only full backtest #38418474184](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184)
- **Corrected code revision:** `fa9cd1593a190fcfa2523dd02bd3697fa2ccd1af`
- **Validated output bundle:** [Download corrected report and three generated parquet outputs](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184/artifacts/11825760496)
- **Input/cache diagnostics:** [Cache manifest, checksums and run diagnostics](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184/artifacts/11825481124)
- **Frozen config:** `config/sectorrotation_candidate_001.yaml`, SHA-256 prefix `4f186de79db3`
- **Input policy:** cache only, no market-data downloads. All 16 required tracked parquet inputs passed preflight; each of the 9 candidate sector ETF caches contained 6,991 complete, positive Close observations from 1998-12-22 through 2026-10-08.
- **Runner checks:** 36 chronological walk-forward folds; finite required train/OOS metrics; persisted weights, daily simulation, trades, date indices, report provenance, configuration hash and executing revision all validated.

## Frozen C4 design

- Universe: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY.
- Candidate history: 1998-12-22 through 2026-10-08 (6,991 common trading days).
- Baseline: cross-sectional momentum, lookback 252, skip 21, top fraction 0.5; monthly rebalance; one-day lag.
- Costs: 1 bp commission + 2 bps slippage = 3 bps per unit of weight change.
- Robustness grid: 3 lookbacks × 2 skips × 3 top fractions = 18 pre-registered configurations.
- Walk-forward: 10-year train, 12-month test, 6-month step, 21-day purge and embargo; exactly 36 folds. Parameters were fixed across folds; no post-hoc tuning.

## Results

| Metric | Observed | Frozen criterion | Status |
|---|---:|---:|---|
| Mean OOS walk-forward Sharpe | **0.6944** | ≥ 0.90 | **FAIL** |
| Positive OOS folds | 83.3% | ≥ 50% | PASS |
| Pooled OOS trades | 158 | > 100 | PASS |
| Plateau at baseline skip/top-fraction | 3/3 lookbacks | ≥ 2/3 | PASS |
| Baseline test-period Sharpe (2018-01-01–2026-10-09) | 0.4679 | Diagnostic | — |
| Baseline test-period grid rank | 5/18 | Diagnostic | — |
| Deflated Sharpe Ratio | -0.2742 (reported probability 0.3920) | Diagnostic | — |

Benchmark context (not additional promotion gates): test-period Sharpe was 0.4430 for the 1/N sector basket and 1.4122 for the incumbent TSMOM candidate. Mean OOS walk-forward Sharpe was 0.7817 for the equal-weight benchmark and 1.2799 for the incumbent. The equal-weight benchmark's constant-weight convention implies little/no observed turnover drag, a known optimistic bias noted in the frozen design.

## Decision

The primary, pre-registered mean OOS Sharpe gate failed. Therefore the hypothesis is **Rejected/Failed**, regardless of the other three gates passing. The grid remains diagnostic; its best configuration is not promoted and no parameters are changed in response to these results.

This is the first valid execution of the frozen C4 design. It should be distinguished from the earlier Cycle 15 run, which incorrectly evaluated C3's 18-ETF universe and 48 folds under C4 artifact names. C3 was independently rejected on its valid evidence; the corrected C4 result now rejects the sector-restricted variant as well.

## Generated output provenance

The validated workflow artifact bundle contains:
- `sectorrotation_baseline_wf_001.md` — the full report including the 36-fold table, all 18 robustness configurations, benchmark comparison and multiple-testing diagnostics;
- `simulation_sectorrotation_001.parquet`;
- `trades_sectorrotation_001.parquet`;
- `weights_sectorrotation_001.parquet`;
- `c4-cache-manifest.json`, `SHA256SUMS.txt`, and execution provenance.

Generated outputs were published as workflow artifacts; the workflow intentionally did not commit binary research outputs back into the repository. The run and its artifact checksums are linked above.
