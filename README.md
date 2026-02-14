# Personal Finance Editor (Desktop GUI)

A fully visual desktop app built with **PySide6 + matplotlib + SQLite** to manage an investment portfolio, inspect allocation, and project a 1-year plan with monthly contributions.

## UI Layout Outline

- **Left Panel: Portfolio Editor**
  - Asset table with columns: symbol, name, category, currency, current value, expected return
  - Buttons: Add, Edit, Delete, Save, Reset Demo Data
- **Right Panel: Analytics & Planning**
  - Donut chart for allocation percentages
  - Monthly contribution input
  - Target weights table (editable)
  - Projection result summary (projected total, absolute gain, % gain)
  - 12-month line chart for total portfolio value

> MVP assumption: currency conversion is not implemented yet; all asset values are treated as the same base currency in charts and projection.

## How to Run (Windows)

```powershell
# 1) Create virtual environment
python -m venv .venv

# 2) Activate
.\.venv\Scripts\Activate.ps1

# 3) Install dependencies
pip install PySide6 matplotlib

# 4) Run GUI
python app.py
```

## Notes for Extension

- Future-ready for adding multi-currency conversion.
- Easy to add live price fetchers/API integrations.
- SQLite DB auto-creates on first launch (`portfolio_editor.db`).
