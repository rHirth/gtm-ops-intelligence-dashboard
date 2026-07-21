DROP VIEW IF EXISTS vw_lead_funnel_summary;

CREATE VIEW vw_lead_funnel_summary AS
SELECT
    COUNT(*) AS total_leads,
    SUM(mql_flag) AS mqls,
    SUM(first_touch_completed) AS first_touch_completed,
    SUM(converted_to_contact) AS converted_to_contact,
    SUM(converted_to_account) AS converted_to_account,
    SUM(converted_to_opportunity) AS converted_to_opportunity,
    ROUND(1.0 * SUM(mql_flag) / COUNT(*), 4) AS mql_rate,
    ROUND(1.0 * SUM(first_touch_completed) / COUNT(*), 4) AS first_touch_rate,
    ROUND(1.0 * SUM(converted_to_contact) / COUNT(*), 4) AS lead_to_contact_rate,
    ROUND(1.0 * SUM(converted_to_account) / COUNT(*), 4) AS lead_to_account_rate,
    ROUND(1.0 * SUM(converted_to_opportunity) / COUNT(*), 4) AS lead_to_opportunity_rate
FROM fact_leads;


DROP VIEW IF EXISTS vw_lead_routing_failures;

CREATE VIEW vw_lead_routing_failures AS
SELECT
    lead_source,
    email_type,
    routing_status,
    routing_failure_reason,
    COUNT(*) AS leads
FROM fact_leads
WHERE routing_status IN (
    'manual_review',
    'fallback_queue',
    'failed_routing',
    'suppressed_duplicate_invalid'
)
GROUP BY
    lead_source,
    email_type,
    routing_status,
    routing_failure_reason;


DROP VIEW IF EXISTS vw_conversion_by_speed_to_lead;

CREATE VIEW vw_conversion_by_speed_to_lead AS
SELECT
    speed_to_lead_bucket,
    COUNT(*) AS leads,
    SUM(mql_flag) AS mqls,
    SUM(first_touch_completed) AS first_touch_completed,
    SUM(converted_to_contact) AS converted_to_contact,
    SUM(converted_to_opportunity) AS converted_to_opportunity,
    ROUND(1.0 * SUM(mql_flag) / COUNT(*), 4) AS mql_rate,
    ROUND(1.0 * SUM(converted_to_contact) / COUNT(*), 4) AS contact_conversion_rate,
    ROUND(1.0 * SUM(converted_to_opportunity) / COUNT(*), 4) AS opportunity_conversion_rate
FROM fact_leads
GROUP BY speed_to_lead_bucket;


DROP VIEW IF EXISTS vw_closed_lost_summary;

CREATE VIEW vw_closed_lost_summary AS
SELECT
    loss_reason_category,
    loss_reason,
    controllable_loss_flag,
    COUNT(*) AS closed_lost_opportunities,
    SUM(amount) AS closed_lost_amount,
    ROUND(AVG(operational_risk_score), 2) AS avg_operational_risk_score
FROM fact_opportunities
WHERE is_closed_lost = 1
GROUP BY
    loss_reason_category,
    loss_reason,
    controllable_loss_flag;


DROP VIEW IF EXISTS vw_closed_lost_by_operational_risk;

CREATE VIEW vw_closed_lost_by_operational_risk AS
SELECT
    operational_risk_score,
    COUNT(*) AS opportunities,
    SUM(is_closed_lost) AS closed_lost_opportunities,
    SUM(is_won) AS closed_won_opportunities,
    SUM(amount) AS total_pipeline_amount,
    SUM(CASE WHEN is_closed_lost = 1 THEN amount ELSE 0 END) AS closed_lost_amount,
    ROUND(1.0 * SUM(is_closed_lost) / COUNT(*), 4) AS closed_lost_rate,
    ROUND(1.0 * SUM(is_won) / COUNT(*), 4) AS closed_won_rate
FROM fact_opportunities
GROUP BY operational_risk_score;


DROP VIEW IF EXISTS vw_ticket_sla_summary;

CREATE VIEW vw_ticket_sla_summary AS
SELECT
    final_owner_team,
    ticket_category,
    priority,
    COUNT(*) AS tickets,
    ROUND(AVG(sla_met), 4) AS sla_met_rate,
    ROUND(AVG(sla_breached), 4) AS sla_breach_rate,
    ROUND(AVG(reassignment_required), 4) AS reassignment_rate,
    ROUND(AVG(hours_to_first_action), 2) AS avg_hours_to_first_action,
    ROUND(AVG(hours_to_resolution), 2) AS avg_hours_to_resolution,
    ROUND(AVG(reassignment_delay_hours), 2) AS avg_reassignment_delay_hours
FROM fact_tickets
GROUP BY
    final_owner_team,
    ticket_category,
    priority;


DROP VIEW IF EXISTS vw_ticket_ai_triage_impact;

CREATE VIEW vw_ticket_ai_triage_impact AS
SELECT
    triage_method,
    post_ai_launch,
    COUNT(*) AS tickets,
    ROUND(AVG(sla_met), 4) AS sla_met_rate,
    ROUND(AVG(sla_breached), 4) AS sla_breach_rate,
    ROUND(AVG(reassignment_required), 4) AS reassignment_rate,
    ROUND(AVG(reassignment_delay_hours), 2) AS avg_reassignment_delay_hours,
    ROUND(AVG(hours_to_first_action), 2) AS avg_hours_to_first_action,
    ROUND(AVG(hours_to_resolution), 2) AS avg_hours_to_resolution
FROM fact_tickets
GROUP BY
    triage_method,
    post_ai_launch;