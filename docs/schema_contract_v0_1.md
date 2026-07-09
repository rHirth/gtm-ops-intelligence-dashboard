# Schema Contract v0.1

This document freezes the current v0.1 schema for the GTM Operations Intelligence Dashboard project.

The purpose of freezing the schema is not to prevent future changes forever. It creates a named baseline so later tables and dashboard queries can be built against a stable set of current columns.

## Freeze Rule

For v0.1, do not rename, remove, or reorder columns in the current CSV outputs unless the schema contract is deliberately updated.

Allowed before v0.2:

- Documentation changes
- Validation output updates
- README updates
- Bug fixes that do not change the declared column list

Not allowed without updating this document:

- Removing columns
- Renaming columns
- Changing primary key fields
- Changing foreign-key-style relationships
- Changing row-count targets
- Changing generated output paths

## Current Tables

### dim_sales_reps

Rows: 83

Output path:

```text
data/processed/dim_sales_reps.csv
```

Columns:

```text
rep_id
rep_name
region
territory_id
team
role
active_flag
capacity_score
```

Primary key:

```text
rep_id
```

### dim_accounts

Rows: 2,250

Output path:

```text
data/processed/dim_accounts.csv
```

Columns:

```text
account_id
account_name
account_domain
account_created_source
account_status
industry
segment
employee_band
estimated_employee_count
annual_revenue_band
country
subregion
region
territory_id
owner_rep_id
account_fit_score
account_fit_tier
data_quality_score
data_quality_tier
domain_quality
account_issue_type
account_dq_root_cause
created_date
```

Primary key:

```text
account_id
```

Foreign-key-style relationship:

```text
dim_accounts.owner_rep_id -> dim_sales_reps.rep_id
```

### fact_leads

Rows: 12,000

Output path:

```text
data/processed/fact_leads.csv
```

Columns:

```text
lead_id
created_at
created_month
created_quarter
routing_model_version
lead_source
region
subregion
country
segment
industry
email
email_domain
email_type
form_completeness
full_name_provided
company_name_provided
job_title_provided
country_provided
inferred_company
inferred_country
inferred_region
account_match_status
matched_account_id
possible_account_id
created_account_id
created_contact_id
job_function
seniority
lead_score
lead_score_band
mql_flag
enrichment_status
enrichment_confidence_score
missing_required_fields_count
routing_status
routing_failure_reason
assignment_method
assigned_rep_id
assigned_territory_id
minutes_to_assignment
first_touch_at
minutes_to_first_touch
speed_to_lead_bucket
first_touch_completed
converted_to_contact
converted_to_account
converted_to_opportunity
created_opportunity_id
conversion_outcome
non_conversion_reason
data_quality_score
data_quality_tier
```

Primary key:

```text
lead_id
```

Foreign-key-style relationships:

```text
fact_leads.assigned_rep_id -> dim_sales_reps.rep_id
fact_leads.matched_account_id -> dim_accounts.account_id
fact_leads.possible_account_id -> dim_accounts.account_id
fact_leads.created_account_id -> dim_accounts.account_id
```

## Current Row Targets

```text
dim_sales_reps: 83 rows
dim_accounts: 2,250 rows
fact_leads: 12,000 rows
```

## Current Conversion Targets

```text
converted contacts: 2,800
converted opportunities: 1,300
```

## Current Generation Order

```text
1. python src/generate_sales_reps.py
2. python src/generate_accounts.py
3. python src/generate_leads.py
```
