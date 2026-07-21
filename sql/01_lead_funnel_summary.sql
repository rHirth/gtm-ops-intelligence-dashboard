SELECT
    COUNT(*) AS total_leads,
    SUM(mql_flag) AS mqls,
    SUM(first_touch_completed) AS first_touch_completed,
    SUM(converted_to_contact) AS converted_to_contact,
    SUM(converted_to_account) AS converted_to_account,
    SUM(converted_to_opportunity) AS converted_to_opportunity,
    ROUND(1.0 * SUM(converted_to_opportunity) / COUNT(*), 4) AS lead_to_opportunity_rate
FROM fact_leads;