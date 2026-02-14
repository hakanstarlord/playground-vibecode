"""Command line interface for personal finance simulator."""

from __future__ import annotations

import argparse
import json
from datetime import date

from .models import Asset, Transaction
from .plotting import plot_deterministic, plot_monte_carlo_band
from .simulation import Simulator
from .storage import PortfolioStorage, seed_demo_data


def parse_weights(raw: str) -> dict[str, float]:
    """Parse target weights from JSON string."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("weights must be valid JSON like '{\"SPY\":0.7,\"AGG\":0.3}'") from exc

    if not isinstance(data, dict) or not data:
        raise ValueError("weights must be a non-empty JSON object")

    parsed: dict[str, float] = {}
    for key, value in data.items():
        parsed[str(key)] = float(value)
    return parsed


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Finance Simulator")
    parser.add_argument("--db", default="finance.db", help="SQLite database path")

    sub = parser.add_subparsers(dest="command", required=True)

    add_asset = sub.add_parser("add-asset", help="Add or update an asset")
    add_asset.add_argument("name")
    add_asset.add_argument("type")
    add_asset.add_argument("currency")
    add_asset.add_argument("expected_return_annual", type=float)
    add_asset.add_argument("volatility_annual", type=float)

    add_tx = sub.add_parser("add-tx", help="Add transaction")
    add_tx.add_argument("date", help="YYYY-MM-DD")
    add_tx.add_argument("asset")
    add_tx.add_argument("action", choices=["buy", "sell", "deposit", "withdraw"])
    add_tx.add_argument("quantity_or_amount", type=float)
    add_tx.add_argument("price", type=float)
    add_tx.add_argument("fee", type=float, nargs="?", default=0.0)

    sub.add_parser("show", help="Show assets, transactions, and current portfolio")

    simulate = sub.add_parser("simulate", help="Run deterministic and monte carlo simulations")
    simulate.add_argument("years", type=int)
    simulate.add_argument("monthly_contribution", type=float)
    simulate.add_argument("weights", help="JSON weights, e.g. '{\"SPY\":0.7,\"AGG\":0.3}'")
    simulate.add_argument("--runs", type=int, default=2000)

    return parser


def run() -> None:
    parser = create_parser()
    args = parser.parse_args()

    storage = PortfolioStorage(db_path=args.db)
    seed_demo_data(storage)

    try:
        if args.command == "add-asset":
            storage.add_asset(
                Asset(
                    name=args.name,
                    type=args.type,
                    currency=args.currency,
                    expected_return_annual=args.expected_return_annual,
                    volatility_annual=args.volatility_annual,
                )
            )
            print(f"Asset '{args.name}' saved.")

        elif args.command == "add-tx":
            storage.add_transaction(
                Transaction(
                    date=date.fromisoformat(args.date),
                    asset=args.asset,
                    action=args.action,
                    quantity_or_amount=args.quantity_or_amount,
                    price=args.price,
                    fee=args.fee,
                )
            )
            print("Transaction saved.")

        elif args.command == "show":
            assets = storage.list_assets()
            txs = storage.list_transactions()
            portfolio = storage.list_portfolio()
            print("Assets:")
            for a in assets:
                print(f"  - {a.name} ({a.type}, {a.currency}) mu={a.expected_return_annual:.2%} sigma={a.volatility_annual:.2%}")
            print("\nTransactions:")
            for t in txs:
                print(f"  - {t.date} {t.action} {t.asset} qty/amt={t.quantity_or_amount} price={t.price} fee={t.fee}")
            print("\nHoldings:", portfolio.holdings)
            print("Cash:", portfolio.cash_balances)

        elif args.command == "simulate":
            weights = parse_weights(args.weights)
            simulator = Simulator(storage)
            result = simulator.simulate(
                years=args.years,
                monthly_contribution=args.monthly_contribution,
                target_weights=weights,
                runs=args.runs,
            )

            det_file = "not generated"
            mc_file = "not generated"
            try:
                det_file = plot_deterministic(result)
                mc_file = plot_monte_carlo_band(result)
            except ModuleNotFoundError:
                print("Warning: matplotlib is not installed. Skipping plot generation.")

            print(f"End values after {args.years}y:")
            print(f"  Deterministic: {result.deterministic[-1]:,.2f}")
            print(f"  P10:           {result.p10[-1]:,.2f}")
            print(f"  Median:        {result.median[-1]:,.2f}")
            print(f"  P90:           {result.p90[-1]:,.2f}")
            print(f"Saved plots: {det_file}, {mc_file}")

    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(2) from exc


if __name__ == "__main__":
    run()
