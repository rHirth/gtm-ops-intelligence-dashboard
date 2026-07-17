# Validation Guide v0.3: Ticket/SLA Layer

Run from the project root:

```powershell
python src/generate_tickets.py | Tee-Object docs/generate_tickets_output.txt
```

Then confirm that the generated outputs are stable:

```powershell
git diff -- data/processed/dim_sla_policy.csv data/processed/fact_tickets.csv
```

Expected output after the generated files are committed and the script is rerun: no diff.

## Built-In Validation Checks

The generator validates:

- Correct columns and column order for `dim_sla_policy`
- Unique `sla_policy_id`
- Valid priorities, categories, and owner teams
- Positive SLA targets
- Correct columns and column order for `fact_tickets`
- Exactly 5,000 tickets
- Unique `ticket_id`
- Required fields populated
- Valid team, priority, category, and triage-method values
- `reassignment_required` equals `initial_team_selected != final_owner_team`
- `sla_met` equals `hours_to_resolution <= sla_target_hours`
- `sla_breached` equals `1 - sla_met`
- `sla_due_at` equals `created_at + sla_target_hours`
- Exactly 2,500 manual-picklist tickets
- Exactly 2,500 AI-assisted tickets
- AI confidence blank for manual tickets and populated for AI-assisted tickets
- `sla_policy_id` values exist in `dim_sla_policy`

## Current Validation Summary

```text
fact_tickets rows: 5,000
dim_sla_policy rows: 48
manual_picklist tickets: 2,500
ai_assisted tickets: 2,500
manual SLA met rate: 0.604
AI-assisted SLA met rate: 0.906
manual reassignment rate: 0.302
AI-assisted reassignment rate: 0.106
```
