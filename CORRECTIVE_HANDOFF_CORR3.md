# Corrective handoff 3

## Profiling result
Single gate-headroom test: 56.33s under cProfile. Dominant cost: `src/backtest/engine.py:59 compute_metrics` invoked 20,138 times, 26.156s cumtime, inside pandas Series/DataFrame operations (isinstance checks, Series construction, reductions). Not import time.

## Verification commands
- `python -m pytest tests/test_cost_admissibility_screen.py::test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom --durations=10 -q` -> 1 passed, 23.29s.
- `timeout 300 python -m pytest -q` -> EXIT=124 at ~9% (full suite cannot complete in 5 min).

## Unresolved blocker
Full suite hangs due to 20k repeated compute_metrics calls in cost_admissibility_screen path. Optimization requires refactoring caller to batch/vectorize; not safe as one-line fix. Next investigation: inspect call sites of compute_metrics within research/cost_admissibility_screen.py and add memoization or reduce trial count.
