# Data Dictionary v0.2: Opportunity Layer

## dim_loss_reasons

| Column | Description |
|---|---|
| `loss_reason_id` | Unique loss reason identifier. |
| `loss_reason` | Human-readable Closed-Lost reason. |
| `loss_reason_category` | Grouped loss reason category. |
| `controllable_flag` | 1 if the loss reason is treated as operationally controllable or partly controllable. |

## fact_opportunities

| Column | Description |
|---|---|
| `opportunity_id` | Unique opportunity identifier. |
| `account_id` | Account associated with the opportunity. |
| `originating_lead_id` | Lead ID when opportunity originated from a converted MQL; blank for sales-generated and expansion opportunities. |
| `owner_rep_id` | Active AE/EAE opportunity owner. |
| `created_at` | Opportunity creation date. |
| `close_date` | Close date for Closed Won / Closed Lost opportunities; blank for open opportunities. |
| `stage` | Current or final opportunity stage. |
| `amount` | Synthetic opportunity amount. |
| `is_closed` | 1 if opportunity is closed. |
| `is_won` | 1 if opportunity is Closed Won. |
| `is_closed_lost` | 1 if opportunity is Closed Lost. |
| `opportunity_source` | Converted MQL, sales-generated, or expansion. |
| `lead_source` | Original lead source for converted-MQL opportunities; blank otherwise. |
| `region` | GTM region. |
| `territory_id` | Sales territory. |
| `segment` | Account/opportunity segment. |
| `industry` | Account/opportunity industry. |
| `sales_cycle_days` | Days from opportunity creation to close; blank for open opportunities. |
| `loss_reason_id` | Loss reason ID for Closed-Lost opportunities. |
| `loss_reason` | Human-readable loss reason for Closed-Lost opportunities. |
| `loss_reason_category` | Grouped loss reason category for Closed-Lost opportunities. |
| `controllable_loss_flag` | 1 if Closed-Lost reason is treated as operationally controllable or partly controllable. |
| `days_in_stage` | Current days in stage for open opportunities; near-zero for closed opportunities. |
| `activity_count` | Synthetic opportunity activity count. |
| `days_since_last_activity` | Days since last opportunity activity. |
| `next_step_exists` | 1 if opportunity has a next step. |
| `operational_risk_score` | Synthetic risk score based on routing, speed-to-lead, data quality, stage age, activity, next step, and rep capacity signals. |
