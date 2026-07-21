SELECT
    lead_source,
    email_type,
    routing_status,
    routing_failure_reason,
    COUNT(*) AS leads
FROM fact_leads
GROUP BY
    lead_source,
    email_type,
    routing_status,
    routing_failure_reason
ORDER BY leads DESC;