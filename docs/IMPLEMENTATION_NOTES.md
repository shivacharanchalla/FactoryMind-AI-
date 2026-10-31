# Implementation notes

## Relationships
- Product 1:N Routing.
- ProductionOrder 1:N Operation.
- Operation 0:1 OperationSchedule in a single schedule version; historical versions should be 1:N in a production deployment.
- Machine 1:N MachineCalendar.
- Machine N:M Operation type through machine_capabilities.
- Product N:M Material through product_materials.
- Material 1:N InventoryLot.
- ChangeoverMatrix defines a directed operation-type pair.

## Lifecycle
Product/routing/machine/material: ACTIVE or INACTIVE.
Order: PLANNED, RELEASED, IN_PROGRESS, COMPLETED, CANCELLED.
Operation schedule: SCHEDULED, UNSCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED.
Schedule changes should be appended to schedule_events with event timestamp, old value, new value, reason and actor.

## Known limitations / honest scope
This starter implementation has a deterministic greedy scheduler, not a globally optimal CP-SAT model. It checks machine eligibility, precedence, shifts, downtime and material arrival. It uses one aggregate lot per material and does not yet reserve/consume material quantities across orders. Labor skill allocation is represented in the source model but not fully optimized. These are explicit extension points, not hidden assumptions.
