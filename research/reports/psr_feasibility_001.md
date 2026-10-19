# PSR Feasibility Analysis (Cycle 864)

## Context
Cycle 863 quantified mechanical roll-off of trailing 63d window: under record-mean continuation (+0.00066578/day) rolling 63d Sharpe crosses 0.9 around +49 sessions mechanically. However PSR remains < 0.95 (0.684) with observed Sharpe 1.748 and SE 0.690150; Cycle 862 showed reaching PSR≥0.95 requires observed Sharpe ≥ 2.552996 at current SE.

## Key numbers (committed record, canonical arithmetic rf=0)
- Committed: 449 sessions (ends 2026-10-16)
- Full-period: mean_daily=0.00066578 (ann=0.167777), std(ddof=1)=0.006045, Sharpe=1.748401
- Trailing 63: mean_daily=-0.00006914, std=0.005180, Sharpe=-0.211884
- PSR (target 1.4178, canonical): psr_normal=0.684041, se=0.690150, observed Sharpe=1.748401

**Requirement:** For PSR≥0.95 at current SE (0.690150), need observed Sharpe ≥ 2.552996.
**Required mean (at current full-period std=0.006045):** mean_req = 2.552996*std/sqrt(252) = 0.00097217 daily (ann=0.244986).
**Gap:** +0.00030638 daily (+0.077209 ann) vs record mean 0.00066578.

## Mechanical effect of continuation on full-period Sharpe
Adding N sessions each with return r_future to a series of n sessions with mean μ_n, std σ_n changes full-period statistics. The projection in Cycle 863 considered rolling window mechanics; here we consider full-period observed Sharpe (numerator side of PSR).

Let’s denote original n=449 with μ_n, σ_n^2 (ddof=1). After adding N sessions at constant r_future:
- μ_{n+N} = (n*μ_n + N*r_future)/(n+N)
- (n+N-1)*σ_{n+N}^2 = (n-1)*σ_n^2 + N*(r_future - μ_{n+N})^2 + n*(μ_n - μ_{n+N})^2 (approx form) — easier to compute numerically.

With r_future = record mean (0.00066578), to reach Sharpe ~2.553 requires very high observed Sharpe — but mechanical addition alone: even with perfect continuation at record mean, the full-period mean slowly approaches 0.00066578; to lift Sharpe from 1.748 to 2.553 needs large N because std also evolves. The required daily mean 0.00097217 is ~46% above record mean — sustained outperformance vs historical record mean is needed just on the numerator.

## Sensitivity (PSR components)
- Observed Sharpe effect dominates: numerator-driven shortfall (Cycle 862). SE is already ~0.69; to reach PSR>=0.95 need SE ≤ ~0.200991 at current observed Sharpe — much more constraining in the other direction, or need much larger observed Sharpe.
- Bootstrap SE fell with tail addition (0.723→0.690) but PSR still fell because observed dropped more.

## Plausibility assessment
- **Numerator gap:** Required +0.000306 daily mean (+7.72% ann) above historical record mean while maintaining similar or lower dispersion is non-trivial given documented overlays.
- **Overlays constrain:** Volatility targeting de-risks in high-vol periods (procyclical lag) — as seen in trailing window decomposition, it cushioned drawdowns but also reduced exposure when signal performed; achieving much higher Sharpe likely requires either higher gross signal efficacy or different risk-taking — not guaranteed by “more of same” at record mean.
- **Costs/turnover:** Already accounted (cost drag small in window but present). Increasing turnover or pushing into less liquid names not present here; current universe fixed.
- **Gate interactions:** To satisfy PSR numerator, need sustained high performance; but rolling 63d Sharpe must also stay ≥0.9. The Cycle 863 projection shows rolling 63d crosses 0.9 mechanically at +49 sessions if record-mean holds — rolling gate becomes easier mechanically; other gates (max DD, rolling 63d max DD) remained PASS on committed record. So rolling gate is not the blocker mechanically; PSR numerator/SE is.
- **Realism:** Record mean 0.00066578 is the historical long-run average of this committed record; needing ~0.00097217 sustained is a material step-up (~46% higher). Without structural improvement in signal efficacy, achieving it consistently enough to drive full-period Sharpe to ~2.553 while preserving dispersion characteristics is plausible only in optimistic continuation — but not mechanically guaranteed and not supported by current evidence.

## What this establishes (and does not)
- **Does:** Quantifies the PSR numerator requirement in canonical terms: +0.000306 daily mean above record mean needed at current std. Mechanical window roll-off doesn’t satisfy PSR; PSR needs sustained higher observed Sharpe.
- **Does not:** Forecast performance or claim it’s achievable. It states the requirement and gap. Promotion requires PSR≥0.95 with credible evidence, independent of mechanical roll-off.
- **Does not:** Change thresholds/gates.

## Verification
- Read-only: uses only `data/processed/paper_trading_state.yaml`. No writes.
- Canonical Sharpe used throughout (arithmetic annualized rf=0). Numbers anchored to `sharpe_convention_audit.py` (full-period Sharpe 1.748401, trailing 63d -0.211884) match.
- Script: `research/psr_feasibility.py` (deterministic).
