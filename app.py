"""Personal Finance Editor desktop app.

A beginner-friendly PySide6 + matplotlib + SQLite application for editing assets,
viewing allocation, and projecting 1-year growth with monthly contributions.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


DB_PATH = "portfolio_editor.db"
CATEGORIES = ["crypto", "metal", "stock", "fund", "cash"]
CURRENCIES = ["TRY", "USD", "EUR"]


@dataclass(slots=True)
class Asset:
    """Investment asset row."""

    symbol: str
    name: str
    category: str
    currency: str
    current_value: float
    expected_annual_return: float


class PortfolioRepository:
    """SQLite repository for assets and plan settings."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    current_value REAL NOT NULL CHECK(current_value >= 0),
                    expected_annual_return REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS target_weights (
                    symbol TEXT PRIMARY KEY,
                    weight REAL NOT NULL CHECK(weight >= 0),
                    FOREIGN KEY(symbol) REFERENCES assets(symbol) ON DELETE CASCADE
                );
                """
            )

    def list_assets(self) -> list[Asset]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM assets ORDER BY symbol").fetchall()
        return [
            Asset(
                symbol=r["symbol"],
                name=r["name"],
                category=r["category"],
                currency=r["currency"],
                current_value=float(r["current_value"]),
                expected_annual_return=float(r["expected_annual_return"]),
            )
            for r in rows
        ]

    def upsert_asset(self, asset: Asset) -> None:
        self._validate_asset(asset)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assets(symbol, name, category, currency, current_value, expected_annual_return)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    category=excluded.category,
                    currency=excluded.currency,
                    current_value=excluded.current_value,
                    expected_annual_return=excluded.expected_annual_return
                """,
                (
                    asset.symbol.upper(),
                    asset.name.strip(),
                    asset.category,
                    asset.currency,
                    asset.current_value,
                    asset.expected_annual_return,
                ),
            )

    def delete_asset(self, symbol: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM target_weights WHERE symbol=?", (symbol.upper(),))
            conn.execute("DELETE FROM assets WHERE symbol=?", (symbol.upper(),))

    def reset_demo_data(self) -> None:
        demo_assets = [
            Asset("BTC", "Bitcoin", "crypto", "USD", 120000.0, 0.15),
            Asset("XAU", "Gold", "metal", "USD", 80000.0, 0.06),
            Asset("SPY", "S&P 500 ETF", "stock", "USD", 150000.0, 0.09),
            Asset("FND", "Balanced Fund", "fund", "USD", 50000.0, 0.07),
            Asset("CASH", "Cash", "cash", "USD", 20000.0, 0.01),
        ]
        with self._connect() as conn:
            conn.execute("DELETE FROM target_weights")
            conn.execute("DELETE FROM assets")
            conn.execute("DELETE FROM settings WHERE key='monthly_contribution'")
            for asset in demo_assets:
                conn.execute(
                    "INSERT INTO assets(symbol, name, category, currency, current_value, expected_annual_return) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        asset.symbol,
                        asset.name,
                        asset.category,
                        asset.currency,
                        asset.current_value,
                        asset.expected_annual_return,
                    ),
                )

            default_weight = 1.0 / len(demo_assets)
            for asset in demo_assets:
                conn.execute(
                    "INSERT INTO target_weights(symbol, weight) VALUES (?, ?)",
                    (asset.symbol, default_weight),
                )
            conn.execute("INSERT INTO settings(key, value) VALUES('monthly_contribution', '5000')")

    def get_monthly_contribution(self) -> float:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='monthly_contribution'").fetchone()
        return float(row["value"]) if row else 0.0

    def set_monthly_contribution(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Monthly contribution cannot be negative.")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value)
                VALUES('monthly_contribution', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (f"{amount}",),
            )

    def get_target_weights(self) -> dict[str, float]:
        with self._connect() as conn:
            rows = conn.execute("SELECT symbol, weight FROM target_weights").fetchall()
        return {r["symbol"]: float(r["weight"]) for r in rows}

    def set_target_weights(self, weights: dict[str, float]) -> None:
        if not weights:
            raise ValueError("At least one target weight is required.")
        for symbol, weight in weights.items():
            if weight < 0:
                raise ValueError(f"Weight for {symbol} cannot be negative.")

        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Target weights must sum to 1.0. Current sum: {total:.4f}")

        with self._connect() as conn:
            conn.execute("DELETE FROM target_weights")
            for symbol, weight in weights.items():
                conn.execute(
                    "INSERT INTO target_weights(symbol, weight) VALUES (?, ?)",
                    (symbol.upper(), weight),
                )

    @staticmethod
    def _validate_asset(asset: Asset) -> None:
        if not asset.symbol.strip():
            raise ValueError("Symbol is required.")
        if asset.current_value < 0:
            raise ValueError("Current value must be >= 0.")
        if not -0.50 <= asset.expected_annual_return <= 1.00:
            raise ValueError("Expected return must be between -0.50 and 1.00.")


class PortfolioService:
    """Business logic for allocation and projection."""

    def allocation_percentages(self, assets: Iterable[Asset]) -> tuple[list[str], list[float]]:
        items = list(assets)
        total = sum(a.current_value for a in items)
        if total <= 0:
            return [], []
        return [a.symbol for a in items], [a.current_value / total for a in items]

    def project_1y(
        self,
        assets: list[Asset],
        monthly_contribution: float,
        weights: dict[str, float],
    ) -> tuple[list[float], float, float]:
        if monthly_contribution < 0:
            raise ValueError("Monthly contribution must be >= 0")

        asset_map = {a.symbol: a for a in assets}
        if not asset_map:
            raise ValueError("Add assets first to run projections.")

        for symbol in weights:
            if symbol not in asset_map:
                raise ValueError(f"Weight references unknown asset: {symbol}")

        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError("Target weights must sum to 1.0")

        values = {a.symbol: a.current_value for a in assets}
        series = [sum(values.values())]

        for _ in range(12):
            for symbol, weight in weights.items():
                values[symbol] += monthly_contribution * weight

            for symbol, current in list(values.items()):
                annual = asset_map[symbol].expected_annual_return
                monthly_growth = (1 + annual) ** (1 / 12) - 1
                values[symbol] = current * (1 + monthly_growth)

            series.append(sum(values.values()))

        final_total = series[-1]
        absolute_gain = final_total - series[0]
        return series, final_total, absolute_gain


class AssetDialog(QDialog):
    """Add/Edit asset dialog with validation-friendly controls."""

    def __init__(self, parent: QWidget | None = None, asset: Asset | None = None, symbol_locked: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asset Editor")
        self.setModal(True)

        self.symbol_input = QLineEdit()
        self.name_input = QLineEdit()
        self.category_input = QComboBox()
        self.category_input.addItems(CATEGORIES)
        self.currency_input = QComboBox()
        self.currency_input.addItems(CURRENCIES)
        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0, 1_000_000_000)
        self.value_input.setDecimals(2)
        self.value_input.setSingleStep(1000)
        self.return_input = QDoubleSpinBox()
        self.return_input.setRange(-0.50, 1.00)
        self.return_input.setDecimals(4)
        self.return_input.setSingleStep(0.01)

        if asset:
            self.symbol_input.setText(asset.symbol)
            self.name_input.setText(asset.name)
            self.category_input.setCurrentText(asset.category)
            self.currency_input.setCurrentText(asset.currency)
            self.value_input.setValue(asset.current_value)
            self.return_input.setValue(asset.expected_annual_return)
        if symbol_locked:
            self.symbol_input.setEnabled(False)

        form = QFormLayout()
        form.addRow("Symbol*", self.symbol_input)
        form.addRow("Name", self.name_input)
        form.addRow("Category", self.category_input)
        form.addRow("Currency", self.currency_input)
        form.addRow("Current Value", self.value_input)
        form.addRow("Expected Annual Return", self.return_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def to_asset(self) -> Asset:
        return Asset(
            symbol=self.symbol_input.text().strip().upper(),
            name=self.name_input.text().strip() or self.symbol_input.text().strip().upper(),
            category=self.category_input.currentText(),
            currency=self.currency_input.currentText(),
            current_value=float(self.value_input.value()),
            expected_annual_return=float(self.return_input.value()),
        )


class MplChart(FigureCanvas):
    """Reusable matplotlib canvas."""

    def __init__(self, width: float = 5.0, height: float = 3.0) -> None:
        self.figure = Figure(figsize=(width, height), tight_layout=True)
        super().__init__(self.figure)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, repo: PortfolioRepository, service: PortfolioService) -> None:
        super().__init__()
        self.repo = repo
        self.service = service

        self.setWindowTitle("Personal Finance Editor")
        self.resize(1300, 760)

        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(6)
        self.assets_table.setHorizontalHeaderLabels(
            ["Symbol", "Name", "Category", "Currency", "Current Value", "Expected Return"]
        )
        self.assets_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.assets_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.assets_table.verticalHeader().setVisible(False)

        self.weights_table = QTableWidget()
        self.weights_table.setColumnCount(2)
        self.weights_table.setHorizontalHeaderLabels(["Symbol", "Target Weight"])
        self.weights_table.verticalHeader().setVisible(False)

        self.monthly_input = QDoubleSpinBox()
        self.monthly_input.setRange(0, 10_000_000_000)
        self.monthly_input.setDecimals(2)
        self.monthly_input.setSingleStep(1000)

        self.result_label = QLabel("Projected Total (12 months): -\nGain: -")
        self.result_label.setWordWrap(True)

        self.allocation_chart = MplChart()
        self.projection_chart = MplChart()

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Portfolio Editor"))
        left_layout.addWidget(self.assets_table)

        button_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        save_btn = QPushButton("Save")
        reset_btn = QPushButton("Reset Demo Data")

        add_btn.clicked.connect(self.add_asset)
        edit_btn.clicked.connect(self.edit_selected_asset)
        del_btn.clicked.connect(self.delete_selected_asset)
        save_btn.clicked.connect(self.save_all)
        reset_btn.clicked.connect(self.reset_demo)

        for btn in [add_btn, edit_btn, del_btn, save_btn, reset_btn]:
            button_row.addWidget(btn)
        left_layout.addLayout(button_row)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        note = QLabel("Allocation chart assumes all current values are in the same base currency (MVP assumption).")
        note.setWordWrap(True)
        note.setStyleSheet("color: #6b7280;")

        allocation_group = QGroupBox("Allocation")
        allocation_layout = QVBoxLayout(allocation_group)
        allocation_layout.addWidget(note)
        allocation_layout.addWidget(self.allocation_chart)

        plan_group = QGroupBox("Monthly Plan & 1-Year Projection")
        plan_layout = QGridLayout(plan_group)
        plan_layout.addWidget(QLabel("Monthly Contribution Amount"), 0, 0)
        plan_layout.addWidget(self.monthly_input, 0, 1)

        save_plan_btn = QPushButton("Save Plan")
        project_btn = QPushButton("Run 1-Year Projection")
        save_plan_btn.clicked.connect(self.save_all)
        project_btn.clicked.connect(self.run_projection)

        plan_layout.addWidget(self.weights_table, 1, 0, 1, 2)
        plan_layout.addWidget(save_plan_btn, 2, 0)
        plan_layout.addWidget(project_btn, 2, 1)
        plan_layout.addWidget(self.result_label, 3, 0, 1, 2)
        plan_layout.addWidget(self.projection_chart, 4, 0, 1, 2)

        right_layout.addWidget(allocation_group)
        right_layout.addWidget(plan_group)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 6)

        layout = QVBoxLayout(root)
        layout.addWidget(splitter)

        self.setStatusBar(QStatusBar())

    def refresh_all(self) -> None:
        try:
            assets = self.repo.list_assets()
            if not assets:
                self.repo.reset_demo_data()
                assets = self.repo.list_assets()

            self._load_assets_table(assets)
            self.monthly_input.setValue(self.repo.get_monthly_contribution())
            self._load_weights_table(assets)
            self.render_allocation_chart(assets)
            self.run_projection()
            self.statusBar().showMessage("Loaded portfolio.", 3000)
        except Exception as exc:  # pylint: disable=broad-except
            self.show_error("Failed to load application data", exc)

    def _load_assets_table(self, assets: list[Asset]) -> None:
        self.assets_table.setRowCount(len(assets))
        for row, asset in enumerate(assets):
            values = [
                asset.symbol,
                asset.name,
                asset.category,
                asset.currency,
                f"{asset.current_value:,.2f}",
                f"{asset.expected_annual_return:.2%}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.assets_table.setItem(row, col, item)
        self.assets_table.resizeColumnsToContents()

    def _load_weights_table(self, assets: list[Asset]) -> None:
        stored = self.repo.get_target_weights()
        self.weights_table.setRowCount(len(assets))

        if not stored and assets:
            uniform = 1.0 / len(assets)
            stored = {a.symbol: uniform for a in assets}

        for row, asset in enumerate(assets):
            symbol_item = QTableWidgetItem(asset.symbol)
            symbol_item.setFlags(symbol_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.weights_table.setItem(row, 0, symbol_item)

            value = stored.get(asset.symbol, 0.0)
            weight_item = QTableWidgetItem(f"{value:.4f}")
            self.weights_table.setItem(row, 1, weight_item)

        self.weights_table.resizeColumnsToContents()

    def render_allocation_chart(self, assets: list[Asset]) -> None:
        ax = self.allocation_chart.figure.clear() or self.allocation_chart.figure.add_subplot(111)
        labels, weights = self.service.allocation_percentages(assets)

        if not labels:
            ax.text(0.5, 0.5, "No data to display", ha="center", va="center")
            ax.axis("off")
        else:
            wedges, _, _ = ax.pie(
                weights,
                labels=labels,
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops={"width": 0.45},
                pctdistance=0.8,
            )
            ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5))
            ax.set_title("Portfolio Allocation")

        self.allocation_chart.draw()

    def _selected_symbol(self) -> str | None:
        selected = self.assets_table.selectedItems()
        if not selected:
            return None
        return selected[0].text()

    def add_asset(self) -> None:
        dialog = AssetDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        asset = dialog.to_asset()
        try:
            existing = {a.symbol for a in self.repo.list_assets()}
            if asset.symbol in existing:
                raise ValueError("Symbol must be unique. Use Edit for existing assets.")
            self.repo.upsert_asset(asset)
            self.refresh_all()
            self.statusBar().showMessage(f"Added {asset.symbol}", 3000)
        except Exception as exc:  # pylint: disable=broad-except
            self.show_error("Could not add asset", exc)

    def edit_selected_asset(self) -> None:
        symbol = self._selected_symbol()
        if not symbol:
            QMessageBox.information(self, "Select Asset", "Please select an asset row to edit.")
            return

        assets = {a.symbol: a for a in self.repo.list_assets()}
        asset = assets.get(symbol)
        if not asset:
            return

        dialog = AssetDialog(self, asset=asset, symbol_locked=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.repo.upsert_asset(dialog.to_asset())
            self.refresh_all()
            self.statusBar().showMessage(f"Updated {symbol}", 3000)
        except Exception as exc:  # pylint: disable=broad-except
            self.show_error("Could not update asset", exc)

    def delete_selected_asset(self) -> None:
        symbol = self._selected_symbol()
        if not symbol:
            QMessageBox.information(self, "Select Asset", "Please select an asset row to delete.")
            return

        answer = QMessageBox.question(
            self,
            "Delete Asset",
            f"Delete {symbol}? This also removes its target weight.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.repo.delete_asset(symbol)
            self.refresh_all()
            self.statusBar().showMessage(f"Deleted {symbol}", 3000)
        except Exception as exc:  # pylint: disable=broad-except
            self.show_error("Could not delete asset", exc)

    def _read_weights_from_ui(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for row in range(self.weights_table.rowCount()):
            symbol_item = self.weights_table.item(row, 0)
            weight_item = self.weights_table.item(row, 1)
            if not symbol_item or not weight_item:
                continue

            symbol = symbol_item.text().strip().upper()
            text = weight_item.text().strip().replace(",", ".")
            try:
                value = float(text)
            except ValueError as exc:
                raise ValueError(f"Invalid weight value for {symbol}: '{text}'") from exc
            weights[symbol] = value
        return weights

    def save_all(self) -> None:
        try:
            monthly = float(self.monthly_input.value())
            weights = self._read_weights_from_ui()

            self.repo.set_monthly_contribution(monthly)
            self.repo.set_target_weights(weights)
            self.refresh_all()
            self.statusBar().showMessage("Saved successfully.", 4000)
        except Exception as exc:  # pylint: disable=broad-except
            self.statusBar().showMessage("Invalid data. Please fix and try again.", 5000)
            self.show_error("Could not save portfolio plan", exc)

    def run_projection(self) -> None:
        try:
            assets = self.repo.list_assets()
            weights = self._read_weights_from_ui() if self.weights_table.rowCount() else self.repo.get_target_weights()
            monthly = float(self.monthly_input.value())

            series, final_total, gain = self.service.project_1y(assets, monthly, weights)
            start = series[0]
            gain_pct = (gain / start * 100) if start else 0.0

            self.result_label.setText(
                f"Projected Total (12 months): {final_total:,.2f}\n"
                f"Absolute Gain: {gain:,.2f}\n"
                f"Percentage Gain: {gain_pct:.2f}%"
            )

            ax = self.projection_chart.figure.clear() or self.projection_chart.figure.add_subplot(111)
            ax.plot(range(13), series, marker="o", linewidth=2)
            ax.set_title("1-Year Portfolio Projection")
            ax.set_xlabel("Month")
            ax.set_ylabel("Total Value")
            ax.grid(alpha=0.3)
            self.projection_chart.draw()

        except Exception as exc:  # pylint: disable=broad-except
            self.result_label.setText("Projection unavailable. Please verify inputs.")
            self.statusBar().showMessage("Invalid weight sum or projection input.", 5000)
            self.show_error("Projection failed", exc)

    def reset_demo(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset Demo Data",
            "This replaces current data with demo assets. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.repo.reset_demo_data()
            self.refresh_all()
            self.statusBar().showMessage("Demo data reset successfully.", 4000)
        except Exception as exc:  # pylint: disable=broad-except
            self.show_error("Failed to reset demo data", exc)

    def show_error(self, title: str, exc: Exception) -> None:
        QMessageBox.critical(self, title, f"{title}.\n\nDetails: {exc}")


def main() -> int:
    """App entrypoint."""
    app = QApplication(sys.argv)
    window = MainWindow(PortfolioRepository(DB_PATH), PortfolioService())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
