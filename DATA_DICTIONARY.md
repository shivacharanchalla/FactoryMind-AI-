# Data dictionary (core fields)

All IDs are immutable strings. Time values use integer minutes from the planning horizon origin.

| Entity | Primary key | Important fields | Validation |
|---|---|---|---|
| Product | product_id | sku, product_name, family, active | SKU unique; active boolean |
| Routing | routing_id | product_id, revision, effective_from/to, status | Product FK; effective_to after effective_from |
| Operation | operation_id | order_id, product_id, sequence, operation_type, duration_min | Order/product FK; sequence positive; duration positive |
| Machine | machine_id | capability, capacity_units_per_hour, status, crew_required | Machine ID unique; capacity and crew positive |
| MachineCalendar | calendar_id | machine_id, day_index, shift_start_min/end, downtime_start/end | Machine FK; end after start; downtime within shift |
| Material | material_id | material_name, unit, active | Material ID unique |
| InventoryLot | lot_id | material_id, quantity, available_min, status | Material FK; quantity nonnegative |
| ProductionOrder | order_id | product_id, quantity, release_min, due_min, priority, status | Product FK; due after release; priority enum |
| OperationSchedule | schedule_id | operation_id, machine_id, start_min, end_min, setup_min, status | Operation/machine FK; end after start |
| ChangeoverMatrix | from_operation_type + to_operation_type | setup_min | Nonnegative setup duration; pair unique |

Additional bridge entities: `machine_capabilities(machine_id, operation_type)` and `product_materials(product_id, material_id, qty_per_unit)`. Their composite pairs must be unique. The `ground_truth` table is an isolated labelled test set, not a scheduler feature.
