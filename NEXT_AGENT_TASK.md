# NEXT_AGENT_TASK.md

## Cycle 925 — Diagnose and remediate rolling_63d_sharpe weakness for incumbent tsmomentum_spytrend_001

### Context
Cycle 924 completed bootstrap CI analysis of within-bucket phase gaps. None of the F2/F3/F4 buckets showed gaps distinguishable from zero at 95% confidence (all CIs crossed zero), indicating apparent state-dependence is consistent with sampling noise in small buckets. The monitoring statement is finalized as a candidate monitoring input only; no gate changes made.

The incumbent `tsmomentum_spytrend_001` remains `Credible Candidate` by published verdict, but promotion gate evaluation shows `rolling_63d_sharpe` failing on the committed 450-session record (e.g. in `tsmomentum_sma175_promotion_gate_eval.py` output: `rolling_63d_sharpe` fails). This is the most concrete blocking issue for promotion. The task is to diagnose why the 63-day rolling Sharpe is weak and propose/test a minimal, evidence-based fix or confirm it's unfixable without changing the core hypothesis.

### Objective
Investigate the rolling 63d Sharpe behavior for the incumbent walk-forward/paper record, identify the source of weakness (regime concentration, tail periods, parameter sensitivity), test minimal reversible fixes only if strongly justified by mechanism, and report findings with a concrete promotion path or definitive blocker.

### Acceptance criteria
1. Read-only diagnosis first: reproduce rolling_63d_sharpe computation on the incumbent's committed paper/trade record; report distribution (min/median/p25/p10), worst windows, overlap with phase buckets from prior cycles, and correlation to market state.
2. Identify concrete failing windows and whether weakness clusters in specific regimes (leverage Cycle 923/924 findings). If clustering matches noise-level buckets from bootstrap, distinguish signal vs noise.
3. If a minimal reversible fix is identified with a clear mechanism (and doesn't change hypothesis/universe/cost model/gates arbitrarily), test it in isolation with full verification. Otherwise, do NOT change production code.
4. Update/add analysis under `research/` (new report/experiment) documenting: failing windows, regime attribution, attempted fixes (or why none), and recommendation (fix path vs blocked).
5. All changes must be read-only or minimal reversible; preserve byte-identical `data/`, `config/` unless change is strictly necessary and justified with evidence. Never modify promotion gates as a "workaround".
6. Add/extend tests only if behavior changes; otherwise just documentation+diagnosis.

### Scope boundaries
- Diagnosis first; changes only if evidence justifies minimal fix tied to mechanism.
- No gate threshold changes, no universe/cost model changes, no hypothesis redefinition.
- May write NEW files under `research/experiments/` / `research/reports/` only.
- Read-only guarantee for `data/`, `config/` where possible; any change must be justified and tested.

### Validation commands
```bash
python research/tsmomentum_sma175_promotion_gate_eval.py
python -m pytest -q tests/test_tsmomentum_sma175_promotion_gate_eval.py
git status --porcelain data/ config/
```

### Evidence artifacts
- New diagnosis report/experiment record under `research/experiments/` or `research/reports/`
- Reproduction commands and observed outputs
- Concrete recommendation with evidence
