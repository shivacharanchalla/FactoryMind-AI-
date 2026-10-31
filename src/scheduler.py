from __future__ import annotations
import pandas as pd
from .config import SHIFT_START, SHIFT_END

PRIORITY_WEIGHT = {"URGENT": 3, "HIGH": 2, "NORMAL": 1}

def _next_work_window(machine_id, start, duration, calendars):
    """Return earliest contiguous working window; downtime and shifts are respected."""
    rows = calendars[calendars.machine_id == machine_id].sort_values("shift_start_min")
    for row in rows.itertuples():
        s = max(int(start), int(row.shift_start_min))
        e = int(row.shift_end_min)
        if row.downtime_start_min == row.downtime_start_min:  # not NaN
            ds, de = int(row.downtime_start_min), int(row.downtime_end_min)
            if s < ds and s + duration <= ds:
                return s
            if s < de:
                s = max(s, de)
        if s + duration <= e:
            return s
    return None

def build_schedule(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    orders = tables["production_orders"].copy()
    ops = tables["order_operations"].copy()
    caps = tables["machine_capabilities"]
    machines = tables["machines"]
    calendars = tables["machine_calendars"]
    inventory = tables["inventory_lots"]
    pm = tables["product_materials"]
    changeovers = tables["changeover_matrix"].set_index(["from_operation_type","to_operation_type"])["setup_min"].to_dict()

    ops = ops.merge(orders[["order_id","release_min","due_min","priority","quantity"]], on="order_id")
    ops["priority_rank"] = ops.priority.map(PRIORITY_WEIGHT).fillna(1)
    ops = ops.sort_values(["priority_rank","due_min","release_min","order_id","sequence"],
                          ascending=[False,True,True,True,True])
    machine_last = {m: {"end":0, "type":None} for m in machines.machine_id}
    order_finish = {}
    rows = []
    schedule_n = 1
    mat_available = {}
    for r in inventory.itertuples():
        mat_available[r.material_id] = int(r.available_min)
    for op in ops.itertuples():
        earliest = max(int(op.release_min), int(order_finish.get(op.order_id, op.release_min)))
        if op.required_material_id is not None and pd.notna(op.required_material_id):
            earliest = max(earliest, mat_available.get(op.required_material_id, 0))
        eligible_types = caps[caps.operation_type == op.operation_type].machine_id.tolist()
        candidates = []
        for mid in eligible_types:
            prev = machine_last[mid]
            setup = 0 if prev["type"] is None else int(changeovers.get((prev["type"], op.operation_type), 0))
            start = _next_work_window(mid, max(earliest, prev["end"] + setup), int(op.duration_min), calendars)
            if start is not None:
                candidates.append((start + int(op.duration_min), start, mid, setup))
        if not candidates:
            rows.append({"schedule_id":f"SCH-2026-{schedule_n:06d}","operation_id":op.operation_id,
                         "order_id":op.order_id,"machine_id":None,"start_min":None,"end_min":None,
                         "setup_min":None,"status":"UNSCHEDULED","exception":"NO_FEASIBLE_MACHINE_WINDOW"})
            schedule_n += 1
            continue
        _, start, mid, setup = min(candidates)
        end = start + int(op.duration_min)
        rows.append({"schedule_id":f"SCH-2026-{schedule_n:06d}","operation_id":op.operation_id,
                     "order_id":op.order_id,"machine_id":mid,"start_min":start,"end_min":end,
                     "setup_min":setup,"status":"SCHEDULED","exception":None})
        schedule_n += 1
        machine_last[mid] = {"end":end,"type":op.operation_type}
        order_finish[op.order_id] = end
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.merge(ops[["operation_id","sequence","operation_type","duration_min","due_min","priority"]],
                              on="operation_id", how="left")
    return result

def calculate_metrics(schedule: pd.DataFrame, orders: pd.DataFrame, machines: pd.DataFrame) -> dict:
    good = schedule[schedule.status == "SCHEDULED"].copy()
    if good.empty:
        return {"scheduled_operations":0,"unscheduled_operations":len(schedule),
                "makespan_hours":0.0,"machine_utilization_pct":0.0,"on_time_delivery_pct":0.0,
                "total_tardiness_hours":0.0}
    makespan = float(good.end_min.max() - good.start_min.min())
    busy = float((good.end_min-good.start_min).sum())
    # Calendar available time is approximated by count of scheduled machine-shift minutes in horizon.
    available = float(len(machines) * 8 * 60 * 14)
    order_end = good.groupby("order_id").end_min.max()
    merged = orders.set_index("order_id").join(order_end.rename("actual_end"))
    completed = merged.dropna(subset=["actual_end"])
    tardiness = (completed.actual_end - completed.due_min).clip(lower=0)
    on_time = float((tardiness == 0).mean()*100) if len(completed) else 0.0
    return {"scheduled_operations":int(len(good)),"unscheduled_operations":int(len(schedule)-len(good)),
            "makespan_hours":round(makespan/60,2),
            "machine_utilization_pct":round(min(100,busy/available*100),2) if available else 0.0,
            "on_time_delivery_pct":round(on_time,2),
            "total_tardiness_hours":round(float(tardiness.sum())/60,2)}
