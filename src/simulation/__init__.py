"""Simulation engine for paper-trading preparation.

Provides deterministic, point-in-time simulation of the validated TSMOM
+ risk-overlay + regime-filter candidate strategy. Designed to reproduce
backtest results exactly while adding trade logs, positions, and risk metrics
suitable for prospective paper-trading monitoring.
"""

from src.simulation.engine import (
    SimulationConfig,
    SimulationResult,
    run_simulation,
)

__all__ = ["SimulationConfig", "SimulationResult", "run_simulation"]
