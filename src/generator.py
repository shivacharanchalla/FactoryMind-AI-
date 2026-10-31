from __future__ import annotations
import hashlib, json, random
from pathlib import Path
import numpy as np
import pandas as pd
from .config import SEED, HORIZON_DAYS, SHIFT_START, SHIFT_END

def _id(prefix: str, n: int, width: int = 6) -> str:
    return f"{prefix}{n:0{width}d}"

def generate_dataset(scale: str = "starter", seed: int = SEED) -> dict[str, pd.DataFrame]:
    if scale not in {"starter", "full"}:
        raise ValueError("scale must be 'starter' or 'full'")
    n_skus, n_machines, n_orders, n_ops, n_materials = (
        (10, 5, 25, 100, 20) if scale == "starter" else (100, 40, 500, 2000, 200)
    )
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    products = pd.DataFrame([{
        "product_id": _id("PROD-2026-", i), "sku": f"SKU-{i:04d}",
        "product_name": f"Product {i:03d}", "family": f"FAM-{(i-1)%5+1:02d}",
        "active": True, "created_at": "2026-01-01T00:00:00"
    } for i in range(1, n_skus+1)])

    machines = []
    for i in range(1, n_machines+1):
        machines.append({"machine_id": f"MACH-{i:03d}", "machine_name": f"Machine {i:03d}",
                         "capability": ["CUT", "DRILL", "ASSEMBLE"][((i-1)//max(1, n_machines//3)) % 3],
                         "capacity_units_per_hour": int(rng.integers(8, 25)),
                         "status": "ACTIVE", "crew_required": int(rng.integers(1, 3))})
    machines = pd.DataFrame(machines)

    routings, operations, op_machine, order_rows, order_ops = [], [], [], [], []
    # Each SKU has a three-step route; operation records are instantiated per order below.
    for i, p in products.iterrows():
        route_id = f"ROUTE-{p.sku}-01"
        routings.append({"routing_id": route_id, "product_id": p.product_id, "revision": 1,
                         "effective_from": "2026-01-01", "effective_to": None, "status": "ACTIVE"})
    # Machine calendars: one day shift with deterministic planned downtime blocks.
    calendars = []
    for m in machines.itertuples():
        for day in range(HORIZON_DAYS):
            start = day*1440 + SHIFT_START
            end = day*1440 + SHIFT_END
            down_start = start + 210 if (day + int(m.machine_id[-3:])) % 7 == 0 else None
            down_end = down_start + 60 if down_start is not None else None
            calendars.append({"calendar_id": f"CAL-{m.machine_id}-{day+1:02d}",
                              "machine_id": m.machine_id, "day_index": day,
                              "shift_start_min": start, "shift_end_min": end,
                              "downtime_start_min": down_start, "downtime_end_min": down_end})
    machine_calendars = pd.DataFrame(calendars)

    materials = pd.DataFrame([{"material_id": _id("MAT-", i, 4), "material_name": f"Raw material {i:03d}",
                               "unit": "kg", "active": True} for i in range(1, n_materials+1)])
    product_materials = []
    for p in products.itertuples():
        mat = materials.iloc[(int(p.sku[-4:])-1) % n_materials]
        product_materials.append({"product_id": p.product_id, "material_id": mat.material_id,
                                  "qty_per_unit": round(float(rng.uniform(0.5, 2.0)), 2)})
    product_materials = pd.DataFrame(product_materials)

    inventory_lots = []
    for mat in materials.itertuples():
        inventory_lots.append({"lot_id": f"LOT-{mat.material_id}-01", "material_id": mat.material_id,
                               "quantity": int(rng.integers(500, 2000)),
                               "available_min": int(rng.integers(0, 3*1440)), "status": "AVAILABLE"})
    inventory_lots = pd.DataFrame(inventory_lots)

    # Orders have 4 operations each; full scale is exactly 2,000 operations.
    for oi in range(1, n_orders+1):
        prod = products.iloc[(oi-1) % n_skus]
        qty = int(rng.integers(10, 80))
        release = int(rng.integers(0, 2*1440))
        due = release + int(rng.integers(3*1440, 9*1440))
        priority = "URGENT" if oi % 31 == 0 else ("HIGH" if oi % 5 == 0 else "NORMAL")
        order_id = _id("ORD-2026-", oi)
        order_rows.append({"order_id": order_id, "product_id": prod.product_id, "quantity": qty,
                           "release_min": release, "due_min": due, "priority": priority,
                           "status": "RELEASED"})
        # Three operations: cut, drill, assemble. For 500 orders, challenge asks 2,000 operations;
        # add a quality inspection as step four.
        durations = [int(rng.integers(35, 75)), int(rng.integers(25, 60)),
                     int(rng.integers(30, 70)), int(rng.integers(15, 30))]
        steps = ["CUT", "DRILL", "ASSEMBLE", "INSPECT"]
        for step, (name, duration) in enumerate(zip(steps, durations), start=1):
            op_id = _id(f"OP-{order_id}-", step, 2)
            order_ops.append({"operation_id": op_id, "order_id": order_id, "product_id": prod.product_id,
                              "sequence": step, "operation_type": name, "duration_min": duration,
                              "required_material_id": product_materials.loc[product_materials.product_id == prod.product_id, "material_id"].iloc[0] if step == 1 else None,
                              "material_qty": round(qty * float(product_materials.loc[product_materials.product_id == prod.product_id, "qty_per_unit"].iloc[0]), 2) if step == 1 else 0.0})
    production_orders = pd.DataFrame(order_rows)
    order_operations = pd.DataFrame(order_ops)

    # Eligibility bridge: a machine can do its capability; inspection can use any assembly machine.
    capabilities = []
    for m in machines.itertuples():
        for op_type in ["CUT", "DRILL", "ASSEMBLE", "INSPECT"]:
            if m.capability == op_type or (op_type == "INSPECT" and m.capability == "ASSEMBLE"):
                capabilities.append({"machine_id": m.machine_id, "operation_type": op_type})
    machine_capabilities = pd.DataFrame(capabilities)

    changeovers = []
    for a in ["CUT", "DRILL", "ASSEMBLE", "INSPECT"]:
        for b in ["CUT", "DRILL", "ASSEMBLE", "INSPECT"]:
            changeovers.append({"from_operation_type": a, "to_operation_type": b,
                                "setup_min": 0 if a == b else (15 if a == "INSPECT" or b == "INSPECT" else 20)})
    changeover_matrix = pd.DataFrame(changeovers)

    # Explicit ground truth scenarios, separate from clean source data.
    ground_truth = pd.DataFrame([
        {"case_id":"GT-001","issue_type":"MACHINE_OVERLAP","severity":"HIGH","expected_detection":True,"description":"Two operations overlap on one machine."},
        {"case_id":"GT-002","issue_type":"PRECEDENCE_VIOLATION","severity":"HIGH","expected_detection":True,"description":"A downstream operation starts before its predecessor finishes."},
        {"case_id":"GT-003","issue_type":"MATERIAL_BEFORE_AVAILABILITY","severity":"HIGH","expected_detection":True,"description":"An operation consumes material before its inventory lot is available."},
        {"case_id":"GT-004","issue_type":"OUTSIDE_SHIFT","severity":"MEDIUM","expected_detection":True,"description":"An operation is scheduled outside a machine shift."},
        {"case_id":"GT-005","issue_type":"CHANGEOVER_OMITTED","severity":"MEDIUM","expected_detection":True,"description":"A sequence-dependent setup interval is omitted."}
    ])
    return {
        "products":products, "routings":pd.DataFrame(routings), "machines":machines,
        "machine_calendars":machine_calendars, "materials":materials, "inventory_lots":inventory_lots,
        "product_materials":product_materials, "production_orders":production_orders,
        "order_operations":order_operations, "machine_capabilities":machine_capabilities,
        "changeover_matrix":changeover_matrix, "ground_truth":ground_truth
    }

def export_dataset(tables: dict[str, pd.DataFrame], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": SEED, "tables": {}}
    for name, df in tables.items():
        csv_path = out_dir / f"{name}.csv"
        json_path = out_dir / f"{name}.json"
        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2)
        digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        manifest["tables"][name] = {"rows": len(df), "sha256": digest}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
