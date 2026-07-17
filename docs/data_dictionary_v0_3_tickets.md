# Data Dictionary v0.3: Ticket/SLA Layer

This document describes the Ticket/SLA package for the GTM Operations Intelligence Dashboard project.

The layer contains one SLA policy dimension and one ticket fact table.

## dim_sla_policy

Rows: 48

| Column | Description |
|---|---|
| `sla_policy_id` | Unique SLA policy identifier for a ticket category and priority combination. |
| `priority` | Ticket priority level: P1, P2, P3, or P4. |
| `ticket_category` | Synthetic support request category. |
| `owner_team` | Team expected to own the request under the SLA policy. |
| `target_resolution_hours` | Target resolution time in hours. |
| `target_first_action_hours` | Target first analyst action time in hours. |

## fact_tickets

Rows: 5,000

| Column | Description |
|---|---|
| `ticket_id` | Unique synthetic ticket identifier. |
| `created_at` | Ticket creation timestamp. |
| `resolved_at` | Ticket resolution timestamp. |
| `ticket_category` | Synthetic support request category. |
| `priority` | Ticket priority level: P1, P2, P3, or P4. |
| `requester_role` | Synthetic role of the requester submitting the support ticket. |
| `initial_team_selected` | Team initially selected by the user picklist or AI-assisted triage. |
| `final_owner_team` | Correct final team responsible for resolution. |
| `triage_method` | manual_picklist before AI launch or ai_assisted after launch. |
| `ai_confidence_score` | AI triage confidence score; blank for manual-picklist tickets. |
| `reassignment_required` | 1 if the initial team was not the final owner team. |
| `reassignment_delay_hours` | Synthetic delay caused by moving a misrouted ticket to the correct team. |
| `hours_to_first_action` | Hours from ticket creation to first analyst action. |
| `hours_to_resolution` | Hours from ticket creation to resolution. |
| `sla_policy_id` | Unique SLA policy identifier for a ticket category and priority combination. |
| `sla_target_hours` | Resolution target copied from the SLA policy. |
| `sla_due_at` | Timestamp when the ticket resolution SLA was due. |
| `sla_met` | 1 if hours_to_resolution is within sla_target_hours. |
| `sla_breached` | 1 if hours_to_resolution exceeds sla_target_hours. |
| `post_ai_launch` | 1 if the ticket was created on or after the AI triage launch date. |
