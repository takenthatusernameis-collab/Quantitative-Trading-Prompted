# Sample Policy Decision (Cycle 904)

## Decision
The long-sample diagnostic's promotion gate table is evaluated on the **common-inception sample** (the first session on which every asset of the universe has a price). The union-sample numbers remain published next to it for continuity with the committed artifact.

- Rule: common_inception = max of per-symbol first dates in the raw cache (re-derived from data/raw at measurement time; never a frozen date)
- Evaluation sample (long-sample diagnostic gate table): `common_inception_slice` (price frame truncated at the common inception before the signal, cost model, universe, lookback/skip/top_fraction and rebalance semantics are applied)
- Warm-up-preserving variant published beside it: `common_inception_window`
- Union sample published beside it for continuity: `union_sample`

## Evidence it rests on
- Evidence artifact: `research/reports/common_inception_sample_audit_001.md` (Cycle 903)
- The numbers move materially with the sample but the verdict does not change (NO-GO on every sample). The union sample is ragged (price width 1→7, 2,640/8,488 sessions with <5 selectable assets). The union max drawdown (-62.24%) is a pre-inception episode.

## What it changes
The incumbent's long-sample numbers (as reported by the long-sample diagnostic):

- Sharpe: 0.5657179297830458 → 0.7020812007943042 / 0.7128971065113597  
- max DD: -0.6224126346564325 → -0.3669795914712545 / -0.3669795914712546  
- PSR: 1.6549061233035153e-08 → 1.9717579528449186e-04 / 2.3747177705301723e-04

(The policy makes the evaluation sample well-defined; the committed artifact `research/reports/promotion_feasibility_backtest_001.md` is not modified by this cycle and continues to publish the union-sample numbers it publishes today.)

## What it does not change
- The incumbent's NO-GO on every sample
- The promotion decision on the paper record
- Every gate, threshold, decision mapping, universe, cost model and Sharpe convention
- The committed artifact `research/reports/promotion_feasibility_backtest_001.md` (byte-identical; not regenerated/edited)
- `src/backtest/engine.py` window semantics (truncation happens in front of the engine in the audit tool)

## Conditions for revisiting it
- A change of universe
- A change of the engine's window semantics
- A new asset in the universe

Policy file: `config/sample_policy.yaml` (schema_version 1). The consuming tool re-derives the common inception from the raw cache and fails closed if the policy is missing, malformed, or names a rule the tool does not implement.
