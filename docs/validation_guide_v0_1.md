# Validation Guide v0.1

This guide explains how to confirm that the current generated files are valid and reproducible.

## Current Validation Method

The current validation is embedded in the three generation scripts. Each script performs checks and prints summary output.

Run from the project root:

```powershell
python src/generate_sales_reps.py | Tee-Object docs/generate_sales_reps_output.txt
python src/generate_accounts.py | Tee-Object docs/generate_accounts_output.txt
python src/generate_leads.py | Tee-Object docs/generate_leads_output.txt
```

Then confirm that regenerated outputs match committed outputs:

```powershell
git status
git diff -- data/processed
```

Expected result:

```text
nothing to commit, working tree clean
```

or no diff under `data/processed` if only documentation output files were updated.

## What Each Script Validates

### generate_sales_reps.py

Expected checks:

- Correct columns and column order
- Unique `rep_id`
- Valid regions
- Valid roles
- Valid `active_flag`
- Numeric `capacity_score`
- One SDR per territory
- One Regional VP per territory
- One Area VP per major region
- US seller reps are Account Executives
- LATAM, EMEA, and APJ territories have Enterprise AE coverage

Expected current output includes:

```text
Validation passed: dim_sales_reps is valid.
Total sales rep rows: 83
```

### generate_accounts.py

Expected checks:

- Loads `dim_sales_reps.csv`
- Validates every non-null `owner_rep_id` exists in `dim_sales_reps.rep_id`
- Validates account owner territory matches the account territory
- Prints region, segment, issue type, data-quality, and missing-field summaries

Expected current output includes:

```text
Total accounts: 2250
Account-owner FK validation:
Passed: every non-null owner_rep_id exists in dim_sales_reps and matches territory.
```

### generate_leads.py

Expected checks:

- Correct columns and column order
- Exactly 12,000 leads
- Unique `lead_id`
- Required columns are not null
- Account IDs referenced by lead fields exist in `dim_accounts`
- Assigned rep IDs exist in `dim_sales_reps`
- Exactly 2,800 converted contacts
- Exactly 1,300 converted opportunities

Expected current output includes:

```text
Validation passed: fact_leads is valid.
Total leads: 12000
```

## Current v0.1 Summary

```text
dim_sales_reps rows: 83
dim_accounts rows: 2,250
fact_leads rows: 12,000
converted contacts: 2,800
converted opportunities: 1,300
```

## Validation Output Files

Recommended committed validation output files:

```text
docs/generate_sales_reps_output.txt
docs/generate_accounts_output.txt
docs/generate_leads_output.txt
```

These files are not source data. They are audit artifacts showing the latest validation run.
