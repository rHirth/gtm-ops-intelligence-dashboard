SELECT
    triage_method,
    COUNT(*) AS tickets,
    ROUND(AVG(sla_met), 4) AS sla_met_rate,
    ROUND(AVG(sla_breached), 4) AS sla_breach_rate,
    ROUND(AVG(reassignment_required), 4) AS reassignment_rate,
    ROUND(AVG(reassignment_delay_hours), 2) AS avg_reassignment_delay_hours,
    ROUND(AVG(hours_to_resolution), 2) AS avg_hours_to_resolution
FROM fact_tickets
GROUP BY triage_method
ORDER BY triage_method;