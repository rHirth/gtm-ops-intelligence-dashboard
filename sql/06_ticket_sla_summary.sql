SELECT
    final_owner_team,
    ticket_category,
    priority,
    COUNT(*) AS tickets,
    ROUND(AVG(sla_met), 4) AS sla_met_rate,
    ROUND(AVG(sla_breached), 4) AS sla_breach_rate,
    ROUND(AVG(hours_to_resolution), 2) AS avg_hours_to_resolution
FROM fact_tickets
GROUP BY
    final_owner_team,
    ticket_category,
    priority
ORDER BY sla_breach_rate DESC;