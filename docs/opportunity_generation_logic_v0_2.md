# Opportunity Generation Logic v0.2

This document summarizes the v0.2 opportunity layer for the GTM Operations Intelligence Dashboard project.

## Purpose

The opportunity layer supports the second dashboard pain point:

```text
Opportunities that close lost
```

The executive question is:

```text
Which Closed-Lost opportunities show signs of preventable GTM process friction?
```

## Inputs

The generator uses the validated v0.1 foundation:

```text
data/processed/dim_accounts.csv
data/processed/dim_sales_reps.csv
data/processed/fact_leads.csv
```

## Outputs

```text
data/processed/dim_loss_reasons.csv
data/processed/fact_opportunities.csv
docs/generate_opportunities_output.txt
```

## Opportunity Sources

The table creates 1,800 opportunities:

```text
converted_mql: 1,300
sales_generated: 350
expansion: 150
```

Converted-MQL opportunities are generated from `fact_leads` where:

```text
converted_to_opportunity = 1
created_opportunity_id is not null
```

Sales-generated and expansion opportunities are generated from existing accounts and do not have `originating_lead_id` populated.

## Outcome Targets

```text
Closed Won: 400
Closed Lost: 800
Open: 600
```

Outcome targets by source:

```text
converted_mql: 310 won, 500 lost, 490 open
sales_generated: 40 won, 240 lost, 70 open
expansion: 50 won, 60 lost, 40 open
```

## Operational Risk Score

The opportunity table includes `operational_risk_score` using the risk signals previously discussed:

```text
routing delay
slow first touch
lead data-quality tier
rep capacity
missing next step
long days since last activity
low activity count
stale stage age
```

The score ranges from 0 to 9.

## Closed-Lost Reasons

Closed-Lost opportunities receive a `loss_reason_id`, `loss_reason`, `loss_reason_category`, and `controllable_loss_flag` from `dim_loss_reasons`.

Loss reasons are weighted by operational risk:

- Higher-risk opportunities are more likely to receive operational, qualification, or data-quality reasons.
- Lower-risk opportunities are more likely to receive commercial, timing, competitive, or product-fit reasons.

## Validation

The generator validates:

```text
fact_opportunities row count = 1,800
opportunity_id is unique
account_id exists in dim_accounts
owner_rep_id exists in active AE/EAE sales reps
converted-MQL opportunities exactly match fact_leads created_opportunity_id / lead_id pairs
non-converted-MQL opportunities do not have originating_lead_id
opportunity source counts match targets
Closed Won / Closed Lost / Open counts match targets
Closed-Lost rows have valid loss_reason_id values
non-Closed-Lost rows have empty loss reason fields
operational_risk_score is between 0 and 9
```
