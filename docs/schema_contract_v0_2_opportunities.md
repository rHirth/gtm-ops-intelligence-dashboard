# Schema Contract v0.2: Opportunity Layer

This document freezes the v0.2 opportunity-layer schema.

## New Tables

```text
dim_loss_reasons
fact_opportunities
```

## dim_loss_reasons

Output path:

```text
data/processed/dim_loss_reasons.csv
```

Columns:

```text
loss_reason_id
loss_reason
loss_reason_category
controllable_flag
```

Primary key:

```text
loss_reason_id
```

## fact_opportunities

Output path:

```text
data/processed/fact_opportunities.csv
```

Columns:

```text
opportunity_id
account_id
originating_lead_id
owner_rep_id
created_at
close_date
stage
amount
is_closed
is_won
is_closed_lost
opportunity_source
lead_source
region
territory_id
segment
industry
sales_cycle_days
loss_reason_id
loss_reason
loss_reason_category
controllable_loss_flag
days_in_stage
activity_count
days_since_last_activity
next_step_exists
operational_risk_score
```

Primary key:

```text
opportunity_id
```

Foreign-key-style relationships:

```text
fact_opportunities.account_id -> dim_accounts.account_id
fact_opportunities.owner_rep_id -> dim_sales_reps.rep_id
fact_opportunities.originating_lead_id -> fact_leads.lead_id
fact_opportunities.loss_reason_id -> dim_loss_reasons.loss_reason_id
```

## Row Counts

```text
dim_loss_reasons: 13 rows
fact_opportunities: 1,800 rows
```

## Opportunity Source Counts

```text
converted_mql: 1,300
sales_generated: 350
expansion: 150
```

## Outcome Counts

```text
Closed Won: 400
Closed Lost: 800
Open: 600
```
