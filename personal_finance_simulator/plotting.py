"""Visualization helpers for simulation outputs."""

from __future__ import annotations

from pathlib import Path

from .simulation import SimulationResult


def plot_deterministic(result: SimulationResult, output_path: str = "deterministic_growth.png") -> str:
    """Plot deterministic growth curve and save image."""
    import matplotlib.pyplot as plt

    out = Path(output_path)
    plt.figure(figsize=(10, 6))
    plt.plot(result.months, result.deterministic, label="Deterministic", linewidth=2)
    plt.xlabel("Month")
    plt.ylabel("Portfolio Value")
    plt.title("Deterministic Portfolio Growth")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    return str(out)


def plot_monte_carlo_band(result: SimulationResult, output_path: str = "monte_carlo_band.png") -> str:
    """Plot Monte Carlo percentile band and save image."""
    import matplotlib.pyplot as plt

    out = Path(output_path)
    plt.figure(figsize=(10, 6))
    plt.plot(result.months, result.median, label="Median", color="tab:blue", linewidth=2)
    plt.fill_between(result.months, result.p10, result.p90, color="tab:blue", alpha=0.2, label="P10-P90")
    plt.plot(result.months, result.p10, color="tab:red", linestyle="--", label="P10")
    plt.plot(result.months, result.p90, color="tab:green", linestyle="--", label="P90")
    plt.xlabel("Month")
    plt.ylabel("Portfolio Value")
    plt.title("Monte Carlo Portfolio Projection")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    return str(out)
