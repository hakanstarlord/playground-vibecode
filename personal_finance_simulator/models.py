"""Domain models for the personal finance simulator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


AssetType = Literal["stock", "bond", "etf", "crypto", "cash", "other"]
ActionType = Literal["buy", "sell", "deposit", "withdraw"]


@dataclass(slots=True)
class Asset:
    """Tradable asset with return assumptions."""

    name: str
    type: AssetType
    currency: str
    expected_return_annual: float
    volatility_annual: float


@dataclass(slots=True)
class Transaction:
    """Portfolio transaction."""

    date: date
    asset: str
    action: ActionType
    quantity_or_amount: float
    price: float
    fee: float = 0.0
