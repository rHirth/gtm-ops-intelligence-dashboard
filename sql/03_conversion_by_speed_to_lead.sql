SELECT
    speed_to_lead_bucket,
    COUNT(*) AS leads,
    SUM(mql_flag) AS mqls,
    SUM(converted_to_opportunity) AS opportunities,
    ROUND(1.0 * SUM(converted_to_opportunity) / COUNT(*), 4) AS opportunity_rate
FROM fact_leads
GROUP BY speed_to_lead_bucket
ORDER BY opportunity_rate DESC;