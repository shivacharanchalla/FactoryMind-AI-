from src.generator import generate_dataset
from src.scheduler import build_schedule
from src.validation import validate_tables, validate_schedule

def test_starter_generation_counts():
    t=generate_dataset("starter")
    assert len(t["products"])==10
    assert len(t["machines"])==5
    assert len(t["production_orders"])==25
    assert len(t["order_operations"])==100

def test_full_generation_counts():
    t=generate_dataset("full")
    assert len(t["products"])==100
    assert len(t["machines"])==40
    assert len(t["production_orders"])==500
    assert len(t["order_operations"])==2000
    assert len(t["materials"])==200

def test_reproducible_generation():
    a=generate_dataset("starter")
    b=generate_dataset("starter")
    for key in a:
        assert a[key].equals(b[key])

def test_master_data_validation():
    t=generate_dataset("starter")
    assert validate_tables(t).passed.all()

def test_scheduler_no_machine_overlap_or_shift_violation():
    t=generate_dataset("starter")
    s=build_schedule(t)
    issues=validate_schedule(s,t["machine_calendars"])
    assert issues.empty
