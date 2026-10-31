import pandas as pd

PKS = {"products":"product_id","routings":"routing_id","machines":"machine_id",
       "materials":"material_id","production_orders":"order_id",
       "order_operations":"operation_id","inventory_lots":"lot_id"}

def validate_tables(tables: dict[str,pd.DataFrame]) -> pd.DataFrame:
    checks=[]
    def add(name, passed, detail): checks.append({"check":name,"passed":bool(passed),"detail":str(detail)})
    for table, key in PKS.items():
        df=tables[table]
        add(f"{table}.{key} unique", df[key].is_unique, f"{df[key].duplicated().sum()} duplicate keys")
        add(f"{table}.{key} non-null", df[key].notna().all(), f"{df[key].isna().sum()} null keys")
    add("routing product foreign keys", tables["routings"].product_id.isin(tables["products"].product_id).all(),"Every routing references a product")
    add("calendar machine foreign keys", tables["machine_calendars"].machine_id.isin(tables["machines"].machine_id).all(),"Every calendar references a machine")
    add("order product foreign keys", tables["production_orders"].product_id.isin(tables["products"].product_id).all(),"Every order references a product")
    add("operation order foreign keys", tables["order_operations"].order_id.isin(tables["production_orders"].order_id).all(),"Every operation references an order")
    add("inventory material foreign keys", tables["inventory_lots"].material_id.isin(tables["materials"].material_id).all(),"Every lot references a material")
    add("positive operation durations", (tables["order_operations"].duration_min>0).all(),"Durations must be positive")
    add("due after release", (tables["production_orders"].due_min>tables["production_orders"].release_min).all(),"Due dates follow release dates")
    add("nonnegative inventory", (tables["inventory_lots"].quantity>=0).all(),"Inventory quantities are nonnegative")
    return pd.DataFrame(checks)

def validate_schedule(schedule: pd.DataFrame, calendars: pd.DataFrame) -> pd.DataFrame:
    issues=[]
    good=schedule[schedule.status=="SCHEDULED"].copy()
    for machine, group in good.groupby("machine_id"):
        group=group.sort_values("start_min")
        previous_end=None
        for row in group.itertuples():
            if previous_end is not None and row.start_min < previous_end:
                issues.append({"issue_type":"MACHINE_OVERLAP","schedule_id":row.schedule_id,"details":f"{machine} overlaps"})
            previous_end=row.end_min
            windows=calendars[calendars.machine_id==machine]
            inside=False
            for w in windows.itertuples():
                if row.start_min>=w.shift_start_min and row.end_min<=w.shift_end_min:
                    if pd.isna(w.downtime_start_min) or row.end_min<=w.downtime_start_min or row.start_min>=w.downtime_end_min:
                        inside=True; break
            if not inside:
                issues.append({"issue_type":"OUTSIDE_SHIFT","schedule_id":row.schedule_id,"details":f"{machine} outside shift or in downtime"})
    return pd.DataFrame(issues, columns=["issue_type","schedule_id","details"])
