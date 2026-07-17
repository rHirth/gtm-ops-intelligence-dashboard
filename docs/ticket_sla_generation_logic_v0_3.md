# Ticket/SLA Generation Logic v0.3

## Purpose

This package simulates Sales Operations support-ticket intake before and after AI-assisted triage. The goal is to support dashboard analysis of misrouting, reassignment delay, backlog/resolution time, and SLA compliance.

## Business Scenario

Before AI launch, requesters selected the destination team from a picklist:

```text
Sales Ops
CRM Eng
Order Ops
```

After AI launch, AI-assisted triage predicts the correct owner team and assigns a confidence score. The simulation intentionally preserves residual misses after AI launch so the data still supports investigation of categories and teams that remain at risk.

## Current Outputs

```text
data/processed/dim_sla_policy.csv
data/processed/fact_tickets.csv
```

## Current Row Counts

```text
dim_sla_policy: 48 rows
fact_tickets: 5,000 rows
```

## AI Launch Date

```text
2024-10-01
```

The generator creates exactly 2,500 manual-picklist tickets before launch and 2,500 AI-assisted tickets after launch.

## Teams

```text
Sales Ops
CRM Eng
Order Ops
```

## Ticket Categories

```text
lead_routing
territory_assignment
account_ownership
opportunity_update
data_quality
reporting_request
forecasting_support
user_access
automation_bug
field_sync_issue
quote_order_issue
contracting_issue
```

## Ownership Logic

Each ticket category maps to a final owner team. The initial team may be correct or incorrect depending on the triage method.

Before AI launch, manual-picklist assignment accuracy is lower, especially for ambiguous or technical categories such as `automation_bug`, `field_sync_issue`, and `data_quality`.

After AI launch, AI-assisted assignment accuracy improves, but does not become perfect.

## SLA Logic

SLA targets are based on priority:

```text
P1: 4 hours
P2: 24 hours
P3: 72 hours
P4: 120 hours
```

First-action targets are also included in `dim_sla_policy`:

```text
P1: 1 hour
P2: 4 hours
P3: 8 hours
P4: 24 hours
```

The ticket fact table stores `sla_met` and `sla_breached` using resolution SLA:

```text
sla_met = hours_to_resolution <= sla_target_hours
sla_breached = 1 - sla_met
```

## Reassignment Logic

If `initial_team_selected` does not equal `final_owner_team`, the ticket is treated as misrouted and `reassignment_required = 1`.

Misrouted manual-picklist tickets receive longer reassignment delays than misrouted AI-assisted tickets.

## Dashboard Questions Supported

1. Did AI-assisted triage reduce misrouted tickets after launch?
2. Did SLA compliance improve after AI-assisted triage launched?
3. Which ticket categories and owner teams still miss SLA most often?
4. How much SLA breach is explained by reassignment delay versus resolution time?
5. Does AI confidence predict assignment accuracy and SLA success?
