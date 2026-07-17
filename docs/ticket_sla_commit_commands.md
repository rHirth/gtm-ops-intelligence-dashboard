# Ticket/SLA Branch Commit Commands

From your branch:

```powershell
git status
python src/generate_tickets.py | Tee-Object docs/generate_tickets_output.txt
git diff -- data/processed/dim_sla_policy.csv data/processed/fact_tickets.csv

git add src/generate_tickets.py `
        data/processed/dim_sla_policy.csv `
        data/processed/fact_tickets.csv `
        docs/generate_tickets_output.txt `
        docs/data_dictionary_v0_3_tickets.md `
        docs/ticket_sla_generation_logic_v0_3.md `
        docs/validation_guide_v0_3_tickets.md

git commit -m "Add synthetic ticket SLA layer"
git push -u origin feature/ticket-sla-layer
```

After committing, rerun the generator and confirm no processed-data diff:

```powershell
python src/generate_tickets.py | Tee-Object docs/generate_tickets_output.txt
git diff -- data/processed/dim_sla_policy.csv data/processed/fact_tickets.csv
```
