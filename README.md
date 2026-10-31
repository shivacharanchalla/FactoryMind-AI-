# FactoryMind AI

A reproducible, synthetic-data manufacturing scheduling demo for the YottaFlex.ai 72-hour challenge.

## Features
- Deterministic master and transaction data generation (seed `20261022`)
- Products, routings, operations, machines, calendars, materials, inventory lots, orders and changeover data
- Feasible baseline scheduling with machine eligibility, operation precedence, shifts, downtime, material availability and setup times
- Explicit labelled negative test cases kept separate from clean input data
- Validation, KPIs, Gantt chart, machine utilization and disruption simulation
- CSV/JSON exports and SQLite persistence

## Quick start (Windows PowerShell)

```powershell
cd FactoryMind_AI
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Generate data and run tests

```powershell
python -m src.generate_data --scale starter
python -m src.generate_data --scale full
pytest -q
```

The app can also generate data from its sidebar. Starter is useful for quick iteration; full uses 100 SKUs, 40 machines, 500 orders, 2,000 operations and 200 materials.

## Important modeling notes
- Time is represented as integer minutes from the synthetic planning horizon start.
- The demo scheduler uses a deterministic constraint-aware heuristic so it runs quickly on a laptop. OR-Tools is included in dependencies for the next optimization iteration; the current schedule is not represented as a mathematically proven global optimum.
- Material availability is checked at operation start. This demo models aggregate material availability per product/material; it does not implement lot-level FEFO consumption or multi-stage inventory reservation.
- Labor is represented by shift capacity and required crew size in the data model; detailed skill-based labor assignment is an extension point.
- Ground truth is stored separately and never used as scheduler input.
- The anomaly injector creates isolated labelled scenarios for testing. It does not corrupt the clean baseline tables.

## Main outputs
`data/exports/` contains CSV and JSON records. `data/factorymind.db` stores generated records. `reports/` contains validation and KPI summaries.

## Reproducibility
The generator uses a fixed seed. Run it twice with the same seed and compare `manifest.json` checksums. `--scale starter` and `--scale full` use the same generation logic.
