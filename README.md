# Personal Finance Simulator (Python)

A modular CLI application for portfolio tracking and forward simulation using deterministic compounding and Monte Carlo analysis.

## Proposed folder structure

```text
personal_finance_simulator/
  __init__.py
  cli.py            # argparse CLI (add-asset, add-tx, show, simulate)
  models.py         # dataclasses: Asset, Transaction
  storage.py        # SQLite schema, CRUD functions, portfolio aggregation
  simulation.py     # deterministic + Monte Carlo engines
  plotting.py       # matplotlib charts
README.md
```

## Features

- Data model with `Asset`, `Transaction`, and `Portfolio` aggregate
- SQLite persistence with required functions:
  - `add_asset()`
  - `add_transaction()`
  - `list_portfolio()`
  - `portfolio_value()`
- Simulation modes:
  - Deterministic monthly compound growth
  - Monte Carlo (>= 2000 runs) with monthly return conversion from annual assumptions
- Outputs median / p10 / p90 outcomes
- Monthly contribution plan allocated by target weights
- CLI commands:
  - `add-asset`
  - `add-tx`
  - `show`
  - `simulate`
- Visualization with matplotlib:
  - Deterministic growth curve
  - Monte Carlo percentile band
- Demo dataset auto-seeded if DB is empty

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install matplotlib numpy
```

## Run

```bash
python -m personal_finance_simulator.cli --db finance.db show
```

---

## README-style example usage

```bash
# 1) Show seeded demo data
python -m personal_finance_simulator.cli --db finance.db show

# 2) Add a custom asset
python -m personal_finance_simulator.cli --db finance.db add-asset QQQ etf USD 0.10 0.22

# 3) Add a transaction
python -m personal_finance_simulator.cli --db finance.db add-tx 2026-01-15 QQQ buy 5 450 1

# 4) Simulate 15 years with monthly contribution and target weights
python -m personal_finance_simulator.cli --db finance.db simulate 15 1000 '{"SPY":0.6,"AGG":0.3,"QQQ":0.1}' --runs 4000

# Output includes end-value deterministic, p10, median, p90
# and saves:
#   deterministic_growth.png
#   monte_carlo_band.png
```
