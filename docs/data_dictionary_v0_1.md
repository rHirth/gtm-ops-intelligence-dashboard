# Data Dictionary v0.1

This document summarizes the current v0.1 tables and columns. It is intentionally limited to the tables already created: `dim_sales_reps`, `dim_accounts`, and `fact_leads`.


## dim_sales_reps

Rows: 83

| Column | pandas dtype | Description |
|---|---|---|
| `rep_id` | `object` | Unique sales representative identifier. |
| `rep_name` | `object` | Synthetic sales representative name. |
| `region` | `object` | Major GTM region: AMER, EMEA, or APJ. |
| `territory_id` | `object` | Sales territory identifier used for assignment and coverage. |
| `team` | `object` | Readable team name associated with territory and region. |
| `role` | `object` | Sales or leadership role. |
| `active_flag` | `int64` | 1 if active in the synthetic sales organization. |
| `capacity_score` | `float64` | Synthetic workload pressure score. |

## dim_accounts

Rows: 2,250

| Column | pandas dtype | Description |
|---|---|---|
| `account_id` | `object` | Unique account identifier. |
| `account_name` | `object` | Synthetic company/account name. |
| `account_domain` | `object` | Synthetic account web/email domain. |
| `account_created_source` | `object` | Whether account is seeded existing or marked as created from converted lead. |
| `account_status` | `object` | Synthetic account status, such as prospect or customer. |
| `industry` | `object` | Synthetic industry category. |
| `segment` | `object` | Synthetic market segment. |
| `employee_band` | `object` | Employee-count band. |
| `estimated_employee_count` | `float64` | Synthetic employee-count estimate. |
| `annual_revenue_band` | `object` | Annual revenue band. |
| `country` | `object` | Account or lead country. |
| `subregion` | `object` | Sales subregion. |
| `region` | `object` | Major GTM region: AMER, EMEA, or APJ. |
| `territory_id` | `object` | Sales territory identifier used for assignment and coverage. |
| `owner_rep_id` | `object` | Account owner rep identifier. |
| `account_fit_score` | `int64` | Synthetic account fit score from 0 to 100. |
| `account_fit_tier` | `object` | High, medium, or low account fit tier. |
| `data_quality_score` | `int64` | Synthetic record quality score. |
| `data_quality_tier` | `object` | Quality tier derived from score. |
| `domain_quality` | `object` | Domain quality classification. |
| `account_issue_type` | `object` | Injected account issue category. |
| `account_dq_root_cause` | `object` | Root cause behind account data-quality issue. |
| `created_date` | `object` | Synthetic record creation date. |

## fact_leads

Rows: 12,000

| Column | pandas dtype | Description |
|---|---|---|
| `lead_id` | `object` | Unique lead identifier. |
| `created_at` | `object` | Lead creation date. |
| `created_month` | `object` | Lead creation month. |
| `created_quarter` | `object` | Lead creation quarter. |
| `routing_model_version` | `object` | Simulated routing program stage based on lead date. |
| `lead_source` | `object` | Synthetic lead source. |
| `region` | `object` | Major GTM region: AMER, EMEA, or APJ. |
| `subregion` | `object` | Sales subregion. |
| `country` | `object` | Account or lead country. |
| `segment` | `object` | Synthetic market segment. |
| `industry` | `object` | Synthetic industry category. |
| `email` | `object` | Synthetic lead email. |
| `email_domain` | `object` | Email domain extracted from email. |
| `email_type` | `object` | Classification of email quality/type. |
| `form_completeness` | `object` | How much optional form data was supplied. |
| `full_name_provided` | `int64` | Flag for whether full name was provided. |
| `company_name_provided` | `int64` | Flag for whether company name was provided. |
| `job_title_provided` | `int64` | Flag for whether job title was provided. |
| `country_provided` | `int64` | Flag for whether country was provided. |
| `inferred_company` | `object` | Company inferred from submitted or domain data. |
| `inferred_country` | `object` | Country inferred from submitted or domain data. |
| `inferred_region` | `object` | Region inferred from country/domain data. |
| `account_match_status` | `object` | Result of lead-to-account matching logic. |
| `matched_account_id` | `object` | Confirmed matched account identifier. |
| `possible_account_id` | `object` | Possible/fuzzy matched account identifier. |
| `created_account_id` | `object` | Account identifier created from converted lead. |
| `created_contact_id` | `object` | Contact identifier created from converted lead. |
| `job_function` | `object` | Synthetic lead job function. |
| `seniority` | `object` | Synthetic lead seniority. |
| `lead_score` | `int64` | Synthetic lead score from 0 to 100. |
| `lead_score_band` | `object` | Lead score category. |
| `mql_flag` | `int64` | 1 if lead qualifies as an MQL. |
| `enrichment_status` | `object` | Result of synthetic enrichment process. |
| `enrichment_confidence_score` | `float64` | Confidence score for enrichment result. |
| `missing_required_fields_count` | `int64` | Count of missing fields needed for good routing. |
| `routing_status` | `object` | Synthetic routing outcome. |
| `routing_failure_reason` | `object` | Reason routing was delayed, failed, or routed to review. |
| `assignment_method` | `object` | Assignment method used for routing. |
| `assigned_rep_id` | `object` | Lead owner/assigned rep identifier. |
| `assigned_territory_id` | `object` | Assigned territory identifier. |
| `minutes_to_assignment` | `float64` | Minutes from lead creation to assignment. |
| `first_touch_at` | `object` | Timestamp of first seller touch. |
| `minutes_to_first_touch` | `float64` | Minutes from lead creation to first touch. |
| `speed_to_lead_bucket` | `object` | Bucketed first-touch timing. |
| `first_touch_completed` | `int64` | 1 if first touch occurred. |
| `converted_to_contact` | `int64` | 1 if lead converted to contact. |
| `converted_to_account` | `int64` | 1 if lead converted or matched to account. |
| `converted_to_opportunity` | `int64` | 1 if lead created an opportunity. |
| `created_opportunity_id` | `object` | Opportunity identifier created from converted lead. |
| `conversion_outcome` | `object` | Detailed conversion result. |
| `non_conversion_reason` | `object` | Synthetic reason for non-conversion. |
| `data_quality_score` | `int64` | Synthetic record quality score. |
| `data_quality_tier` | `object` | Quality tier derived from score. |
