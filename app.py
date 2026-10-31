import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import streamlit as st
import pandas as pd
import plotly.express as px
from src.generator import generate_dataset, export_dataset
from src.scheduler import build_schedule, calculate_metrics
from src.validation import validate_tables, validate_schedule
from src.config import EXPORT_DIR, DB_PATH
from src.db import save_tables

st.set_page_config(page_title="FactoryMind AI",page_icon="🏭",layout="wide")
st.title("🏭 FactoryMind AI")
st.caption("Constraint-aware production scheduling and factory intelligence")

with st.sidebar:
    st.header("Configuration")
    scale=st.selectbox("Dataset size",["starter","full"],index=0)
    seed=st.number_input("Random seed",value=20261022,step=1)
    generate=st.button("Generate factory data",type="primary",use_container_width=True)
    run=st.button("Build production schedule",use_container_width=True)

if "tables" not in st.session_state:
    st.session_state.tables=generate_dataset("starter")
if generate:
    st.session_state.tables=generate_dataset(scale,int(seed))
    st.session_state.schedule=None
    st.success("Factory data generated.")
if run or "schedule" not in st.session_state or st.session_state.get("schedule") is None:
    st.session_state.schedule=build_schedule(st.session_state.tables)

tables=st.session_state.tables
schedule=st.session_state.schedule
metrics=calculate_metrics(schedule,tables["production_orders"],tables["machines"])
c1,c2,c3,c4=st.columns(4)
c1.metric("Production orders",f"{len(tables['production_orders']):,}")
c2.metric("Machines",f"{len(tables['machines']):,}")
c3.metric("Scheduled operations",f"{metrics['scheduled_operations']:,}")
c4.metric("Unscheduled operations",f"{metrics['unscheduled_operations']:,}")

tabs=st.tabs(["Overview","Production schedule","Machines & inventory","Data quality","Exceptions & exports"])
with tabs[0]:
    st.subheader("Production performance")
    k1,k2,k3=st.columns(3)
    k1.metric("Makespan",f"{metrics['makespan_hours']} h")
    k2.metric("Machine utilization",f"{metrics['machine_utilization_pct']}%")
    k3.metric("On-time delivery",f"{metrics['on_time_delivery_pct']}%")
    k4,k5=st.columns(2)
    k4.metric("Total tardiness",f"{metrics['total_tardiness_hours']} h")
    k5.metric("Unscheduled operations",metrics["unscheduled_operations"])
    st.info("The current scheduler is a deterministic, constraint-aware heuristic. Metrics are calculated from generated records.")
    st.dataframe(pd.DataFrame([{"metric":k,"value":v} for k,v in metrics.items()]),use_container_width=True)
with tabs[1]:
    st.subheader("Machine schedule")
    view=schedule[schedule.status=="SCHEDULED"].copy()
    if not view.empty:
        view["Start (hours)"]=view.start_min/60
        view["Duration (hours)"]=(view.end_min-view.start_min)/60
        fig=px.timeline(view,x_start=view.start_min.apply(lambda x: pd.Timestamp("2026-01-01")+pd.Timedelta(minutes=int(x))),
                        x_end=view.end_min.apply(lambda x: pd.Timestamp("2026-01-01")+pd.Timedelta(minutes=int(x))),
                        y="machine_id",color="operation_type",hover_data=["order_id","operation_id","setup_min"])
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig,use_container_width=True)
    st.dataframe(schedule,use_container_width=True)
with tabs[2]:
    st.subheader("Machine capacity")
    util=schedule[schedule.status=="SCHEDULED"].groupby("machine_id").apply(
        lambda g:(g.end_min-g.start_min).sum(),include_groups=False).reset_index(name="busy_minutes")
    util= tables["machines"][["machine_id","capability"]].merge(util,on="machine_id",how="left").fillna({"busy_minutes":0})
    st.plotly_chart(px.bar(util,x="machine_id",y="busy_minutes",color="capability",title="Scheduled processing minutes by machine"),use_container_width=True)
    st.subheader("Inventory lots")
    st.dataframe(tables["inventory_lots"],use_container_width=True)
with tabs[3]:
    st.subheader("Master and transaction data validation")
    report=validate_tables(tables)
    passed=int(report.passed.sum())
    st.metric("Checks passed",f"{passed}/{len(report)}")
    st.dataframe(report,use_container_width=True)
    sched_issues=validate_schedule(schedule,tables["machine_calendars"])
    st.subheader("Schedule validation")
    if sched_issues.empty: st.success("No machine overlap or shift-calendar violations found in generated schedule.")
    else: st.dataframe(sched_issues,use_container_width=True)
with tabs[4]:
    st.subheader("Known negative test scenarios")
    st.dataframe(tables["ground_truth"],use_container_width=True)
    st.caption("Ground-truth labels are kept separate from clean scheduling input.")
    if st.button("Export CSV / JSON and save SQLite database"):
        manifest=export_dataset(tables,EXPORT_DIR)
        save_tables(tables,DB_PATH)
        schedule.to_csv(EXPORT_DIR/"operation_schedules.csv",index=False)
        pd.DataFrame([metrics]).to_json(EXPORT_DIR/"evaluation_metrics.json",orient="records",indent=2)
        st.success(f"Exported {len(manifest['tables'])} tables to {EXPORT_DIR}")
        st.write("Database:",str(DB_PATH))
