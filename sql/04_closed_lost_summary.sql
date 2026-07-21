SELECT
    loss_reason_category,
    loss_reason,
    controllable_loss_flag,
    COUNT(*) AS closed_lost_opportunities,
    SUM(amount) AS closed_lost_amount
FROM fact_opportunities
WHERE is_closed_lost = 1
GROUP BY
    loss_reason_category,
    loss_reason,
    controllable_loss_flag
ORDER BY closed_lost_amount DESC;