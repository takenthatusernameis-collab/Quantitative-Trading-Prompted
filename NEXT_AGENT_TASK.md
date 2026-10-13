# Next Agent Task: Cycle 16 - Move from Cross-Sectional Momentum (C3/C4) to a Distinct Mechanism

## Context

Cycle 15 completed evaluation of Candidate C4 (`sectorrotation_001`, 9 GICS sector ETFs). Per the frozen hypothesis and Cycle 14→15 task, results:
- Baseline test Sharpe (2018-01-01 to 2026-10-09): 0.4101
- Walk-forward mean OOS Sharpe (36 folds): 0.6868 (< 0.9 gate)
- Positive fold rate: 79.2% (>= 50%)
- Pooled OOS trades: 313 (> 100)
- Plateau: 2/3 lookbacks within 10% of baseline (PASS)
- Deflated Sharpe Ratio (N=18): -0.4634 (DSR p=0.3215); both C3 (broad 18-ETF universe, WF mean 0.6868) and C4 (sector subset) failed the pre-registered 0.9 WF mean Sharpe gate.
- Promotion gates failed (gate 1: WF mean OOS Sharpe < 0.9) → **Rejected/Failed**.

## Objective

Produce ONE narrow, testable next task. Since two pre-registered cross-sectional momentum variants (C3: broad universe, C4: sector-restricted subset) both failed to clear the 0.9 WF mean Sharpe gate after realistic costs (3 bps round-trip), the cross-sectional momentum family in this dataset is rejected for now. Advance to the next distinct mechanism on the shortlist, following the Cycle 15 decision tree.

## Required Actions

1. **Document consolidation**: Add a concise note to `research/experiments/sectorrotation_baseline_wf_001.md` final section if not already present, or to a new `research/reports/cross_momentum_consolidation.md` summarizing:
   - C3 (csmomentum_001, broad 18-ETF universe): WF mean 0.6868, Rejected/Failed
   - C4 (sectorrotation_001, 9 sector ETFs): WF mean 0.6868, Rejected/Failed
   - Both use identical cost model, schedule, splits/WF design; C4 is a subset test of the same mechanism (lower prior). Results consistent.
   - Net-of-cost cross-sectional momentum does not meet the pre-registered promotion gate in this US ETF cache. Not a configuration selection artifact (grid showed no strong plateau improvement).

2. **Select next candidate**: Move to **Candidate C6 (Calendar/rebalancing effects, month-end/quarter-end/index reconstitution flows)** from `research/reports/opportunity_shortlist.md` (score 26/35) as the next distinct mechanism family. Briefly justify the choice (different from momentum, feasible with cached daily data, deterministic calendar rules, diversifies mechanism set). Alternatively consider C8 if C6 is blocked, but C6 is the intended next step per decision tree logic.

3. **Create pre-registration**: Prepare hypothesis and frozen config for the selected next candidate (name, e.g. `calendar_effects_001`) mirroring the discipline of prior cycles:
   - Mechanism, expected direction/magnitude (conservative), holding horizon, universe (SPY/QQQ/IWM primary, specify), features, entry/exit rules, falsification condition.
   - Costs 3 bps round-trip, 1-day lag, monthly/short-horizon as appropriate, no overlays initially.
   - WF design: use standard 10y/12m/6m, 21d purge/embargo, fixed baseline, 18–27 config diagnostic grid as appropriate, pre-registered trial count = actual grid size, assert fold count (use `generate_walkforward_splits`), promotion gates consistent with AGENTS.md (WF mean OOS Sharpe >= 0.9, >=50% positive folds, pooled trades > 100, plateau as specified).
   - Data integrity (cache-only), point-in-time treatment, no lookahead.

4. **Write NEXT_AGENT_TASK.md for Cycle 17**: Specify exact files to create (`research/hypotheses/calendar_effects_001.md`, `config/calendar_effects_001.yaml`), pre-execution assertions, benchmarks (1/N as applicable, incumbent TSMOM as context), DSR/PSR/PBO with true trial count, acceptance criteria, verification commands (test file existence, config parse, prior cycles still run, etc.), scope boundaries (do NOT modify frozen C3/C4 artifacts).

## Acceptance Criteria
- Consolidation documented (brief, evidence-based, no rewriting of C3/C4 records).
- Hypothesis `research/hypotheses/calendar_effects_001.md` created, content matches cycle standards.
- Frozen config `config/calendar_effects_001.yaml` created with explicit `multiple_testing.total_configs = true_product`, expected_folds from splits check, promotion gates.
- `NEXT_AGENT_TASK.md` written for Cycle 17 with concrete commands to validate the pre-registration and run evaluation.
- README/Current Status updated to reflect Cycle 16 transition (brief).
- Validation: frozen config parses (`python3 -c "import yaml; yaml.safe_load(open('config/calendar_effects_001.yaml'))"`), hypothesis file exists, NEXT_AGENT_TASK.md for Cycle 17 present.

## Scope Boundaries
- Do NOT modify `research/hypotheses/sectorrotation_001.md`, `config/sectorrotation_candidate_001.yaml`, or `research/experiments/sectorrotation_baseline_wf_001.md` (frozen C4).
- Do NOT modify C3 frozen artifacts.
- Do NOT add data fetching, new dependencies, overlays, or gate weakening.
- Research/backtesting only.

## Evidence References
- `research/experiments/sectorrotation_baseline_wf_001.md` (Cycle 15)
- `research/experiments/csmomentum_baseline_wf_001.md` (Cycle 13, for consolidation)
- `research/reports/opportunity_shortlist.md` (C6)
