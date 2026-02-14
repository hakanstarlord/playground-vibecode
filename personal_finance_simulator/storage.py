"""SQLite storage and portfolio aggregation logic."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .models import ActionType, Asset, Transaction


@dataclass(slots=True)
class Portfolio:
    """Aggregated portfolio state."""

    holdings: dict[str, float]
    cash_balances: dict[str, float]


class PortfolioStorage:
    """Persistence layer and required portfolio operations."""

    def __init__(self, db_path: str = "finance.db") -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    name TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    expected_return_annual REAL NOT NULL,
                    volatility_annual REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity_or_amount REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(asset) REFERENCES assets(name)
                );
                """
            )

    def add_asset(self, asset: Asset) -> None:
        self._validate_asset(asset)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets(name, type, currency, expected_return_annual, volatility_annual)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    asset.name,
                    asset.type,
                    asset.currency.upper(),
                    asset.expected_return_annual,
                    asset.volatility_annual,
                ),
            )

    def add_transaction(self, tx: Transaction) -> None:
        self._validate_transaction(tx)
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM assets WHERE name=?", (tx.asset,)).fetchone()
            if not exists:
                raise ValueError(f"Unknown asset '{tx.asset}'. Add it first with add-asset.")
            conn.execute(
                """
                INSERT INTO transactions(date, asset, action, quantity_or_amount, price, fee)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (tx.date.isoformat(), tx.asset, tx.action, tx.quantity_or_amount, tx.price, tx.fee),
            )

    def list_assets(self) -> list[Asset]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM assets ORDER BY name").fetchall()
        return [
            Asset(
                name=r["name"],
                type=r["type"],
                currency=r["currency"],
                expected_return_annual=r["expected_return_annual"],
                volatility_annual=r["volatility_annual"],
            )
            for r in rows
        ]

    def list_transactions(self) -> list[Transaction]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM transactions ORDER BY date, id").fetchall()
        return [
            Transaction(
                date=date.fromisoformat(r["date"]),
                asset=r["asset"],
                action=r["action"],
                quantity_or_amount=r["quantity_or_amount"],
                price=r["price"],
                fee=r["fee"],
            )
            for r in rows
        ]

    def list_portfolio(self) -> Portfolio:
        holdings: dict[str, float] = {}
        cash: dict[str, float] = {}

        with self._connect() as conn:
            tx_rows = conn.execute(
                """
                SELECT t.*, a.currency
                FROM transactions t
                JOIN assets a ON a.name = t.asset
                ORDER BY date, id
                """
            ).fetchall()

        for row in tx_rows:
            asset = row["asset"]
            action: ActionType = row["action"]
            qty = float(row["quantity_or_amount"])
            price = float(row["price"])
            fee = float(row["fee"])
            ccy = row["currency"]

            holdings.setdefault(asset, 0.0)
            cash.setdefault(ccy, 0.0)

            if action == "deposit":
                cash[ccy] += qty
            elif action == "withdraw":
                cash[ccy] -= qty
            elif action == "buy":
                holdings[asset] += qty
                cash[ccy] -= qty * price + fee
            elif action == "sell":
                holdings[asset] -= qty
                cash[ccy] += qty * price - fee
            else:
                raise ValueError(f"Unsupported transaction action: {action}")

        holdings = {k: v for k, v in holdings.items() if abs(v) > 1e-10}
        cash = {k: v for k, v in cash.items() if abs(v) > 1e-10}
        return Portfolio(holdings=holdings, cash_balances=cash)

    def portfolio_value(self, price_map: dict[str, float]) -> float:
        portfolio = self.list_portfolio()
        total = 0.0

        for asset, qty in portfolio.holdings.items():
            if asset not in price_map:
                raise ValueError(f"Missing price for asset '{asset}' in price_map.")
            total += qty * price_map[asset]

        total += sum(portfolio.cash_balances.values())
        return total

    def get_asset_map(self) -> dict[str, Asset]:
        return {asset.name: asset for asset in self.list_assets()}

    @staticmethod
    def _validate_asset(asset: Asset) -> None:
        if not asset.name.strip():
            raise ValueError("Asset name cannot be empty.")
        if asset.expected_return_annual < -0.99:
            raise ValueError("expected_return_annual must be greater than -0.99.")
        if asset.volatility_annual < 0:
            raise ValueError("volatility_annual cannot be negative.")

    @staticmethod
    def _validate_transaction(tx: Transaction) -> None:
        if tx.action not in {"buy", "sell", "deposit", "withdraw"}:
            raise ValueError("action must be one of: buy, sell, deposit, withdraw")
        if tx.quantity_or_amount <= 0:
            raise ValueError("quantity_or_amount must be positive.")
        if tx.price < 0:
            raise ValueError("price cannot be negative.")
        if tx.fee < 0:
            raise ValueError("fee cannot be negative.")


def seed_demo_data(storage: PortfolioStorage) -> None:
    """Seed a small dataset if database is empty."""
    if storage.list_assets():
        return

    storage.add_asset(Asset("SPY", "etf", "USD", 0.08, 0.17))
    storage.add_asset(Asset("AGG", "bond", "USD", 0.035, 0.06))

    storage.add_transaction(Transaction(date=date(2025, 1, 1), asset="SPY", action="deposit", quantity_or_amount=10000, price=1, fee=0))
    storage.add_transaction(Transaction(date=date(2025, 1, 2), asset="SPY", action="buy", quantity_or_amount=20, price=500, fee=1))
    storage.add_transaction(Transaction(date=date(2025, 1, 2), asset="AGG", action="buy", quantity_or_amount=10, price=100, fee=1))


def as_dict_list(rows: list[Any]) -> list[dict[str, Any]]:
    """Helper to serialize dataclass-like rows for cli display."""
    return [asdict(row) for row in rows]
