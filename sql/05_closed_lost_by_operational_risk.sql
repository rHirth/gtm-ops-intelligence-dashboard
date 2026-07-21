SELECT
    operational_risk_score,
    COUNT(*) AS opportunities,
    SUM(is_closed_lost) AS closed_lost,
    ROUND(1.0 * SUM(is_closed_lost) / COUNT(*), 4) AS closed_lost_rate
FROM fact_opportunities
GROUP BY operational_risk_score
ORDER BY operational_risk_score;