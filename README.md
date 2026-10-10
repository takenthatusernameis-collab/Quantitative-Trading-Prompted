# Quantitative Trading Research

Autonomous research pipeline for discovering reproducible, net-of-cost trading edges.

## Overview

This repository implements a disciplined quantitative research process focused on finding genuine market inefficiencies that can be captured by low-friction automated strategies. The system runs autonomous agent cycles that iterate through hypothesis formation, implementation, evaluation, and learning.

## Research Philosophy

- **Evidence over optimism**: Prioritize reproducible, net-of-cost results over impressive in-sample backtests
- **Structure over patterns**: Seek specific structural mechanisms (funding/carry, constraints, session effects, delayed discovery) rather than data-mined correlations
- **Honest accounting**: All results reported net of realistic fees, slippage, and market impact
- **Statistical rigor**: Control for multiple testing, use chronological out-of-sample evaluation, track hypothesis count

## Project Structure

```
├── AGENTS.md              # Agent cycle instructions
├── README.md              # This file
├── NEXT_AGENT_TASK.md     # Current task specification
├── PROMPT.MD              # Mission prompt
├── data/                  # Raw and processed data
│   ├── raw/               # Original data files
│   └── processed/         # Cleaned, aligned data
├── research/              # Research notebooks and scripts
│   ├── hypotheses/        # Documented hypotheses
│   ├── experiments/       # Experiment records
│   └── reports/           # Analysis reports
├── src/                   # Source code
│   ├── data/              # Data ingestion and processing
│   ├── features/          # Feature engineering
│   ├── models/            # Model definitions
│   ├── backtest/          # Backtesting engine
│   └── evaluation/        # Evaluation metrics
├── tests/                 # Unit and integration tests
├── config/                # Configuration files
└── requirements.txt       # Python dependencies
```

## Current Status

**Cycle 1**: Initial project setup and market opportunity inventory

## Running the Research Pipeline

The pipeline runs automatically via GitHub Actions every 5 minutes. Each cycle:
1. Reads the current task from `NEXT_AGENT_TASK.md`
2. Executes the bounded research task
3. Produces evidence artifacts
4. Writes the next task to `NEXT_AGENT_TASK.md`

## Key Documents

- [AGENTS.md](AGENTS.md) - Complete agent instructions and research standards
- [NEXT_AGENT_TASK.md](NEXT_AGENT_TASK.md) - Current cycle task specification
- [PROMPT.MD](PROMPT.MD) - Mission prompt

## Research Documentation Standards

All hypotheses and experiments follow strict documentation requirements defined in AGENTS.md to ensure reproducibility and prevent false discoveries.

## Safety

This is a research/backtesting system only. It never places live trades, accesses credentials, or modifies account settings.