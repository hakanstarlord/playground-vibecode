"""Deterministic and Monte Carlo simulation engines."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .storage import PortfolioStorage


@dataclass(slots=True)
class SimulationResult:
    months: np.ndarray
    deterministic: np.ndarray
    p10: np.ndarray
    median: np.ndarray
    p90: np.ndarray


class Simulator:
    """Portfolio growth simulator."""

    def __init__(self, storage: PortfolioStorage) -> None:
        self.storage = storage

    def simulate(
        self,
        years: int,
        monthly_contribution: float,
        target_weights: dict[str, float],
        runs: int = 2000,
    ) -> SimulationResult:
        if years <= 0:
            raise ValueError("years must be > 0")
        if runs < 2000:
            raise ValueError("runs must be >= 2000")
        if monthly_contribution < 0:
            raise ValueError("monthly_contribution cannot be negative")
        self._validate_weights(target_weights)

        months = years * 12
        month_index = np.arange(months + 1)

        asset_map = self.storage.get_asset_map()
        portfolio = self.storage.list_portfolio()

        base_value = sum(portfolio.cash_balances.values())
        for asset_name, qty in portfolio.holdings.items():
            base_value += qty * 1.0

        mus = np.array([asset_map[a].expected_return_annual for a in target_weights])
        sigmas = np.array([asset_map[a].volatility_annual for a in target_weights])
        weights = np.array([target_weights[a] for a in target_weights])

        mu_m = (1 + mus) ** (1 / 12) - 1
        sigma_m = sigmas / math.sqrt(12)

        deterministic = np.zeros(months + 1)
        deterministic[0] = base_value
        weighted_mu = float(np.dot(weights, mu_m))
        for t in range(1, months + 1):
            deterministic[t] = deterministic[t - 1] * (1 + weighted_mu) + monthly_contribution

        mc = np.zeros((runs, months + 1))
        mc[:, 0] = base_value
        rng = np.random.default_rng(42)

        for t in range(1, months + 1):
            returns = rng.normal(loc=mu_m, scale=sigma_m, size=(runs, len(weights)))
            portfolio_return = (returns * weights).sum(axis=1)
            mc[:, t] = mc[:, t - 1] * (1 + portfolio_return) + monthly_contribution

        p10 = np.percentile(mc, 10, axis=0)
        median = np.percentile(mc, 50, axis=0)
        p90 = np.percentile(mc, 90, axis=0)

        return SimulationResult(months=month_index, deterministic=deterministic, p10=p10, median=median, p90=p90)

    def _validate_weights(self, target_weights: dict[str, float]) -> None:
        if not target_weights:
            raise ValueError("target_weights cannot be empty")

        asset_names = set(self.storage.get_asset_map().keys())
        for name, w in target_weights.items():
            if name not in asset_names:
                raise ValueError(f"Unknown asset in target_weights: {name}")
            if w < 0:
                raise ValueError("weights cannot be negative")

        total = sum(target_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError("target_weights must sum to 1.0")
