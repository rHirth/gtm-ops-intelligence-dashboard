# Data Generation Logic v0.1

This document summarizes the current data-generation logic already used in v0.1. It does not introduce new features.

## Project Narrative

The current dataset simulates a global GTM Operations environment where lead conversion is affected by lead source, form completeness, email quality, account matching, enrichment, routing outcome, assignment delay, speed-to-lead, and sales coverage.

The purpose is to demonstrate diagnostic workflow, not to make empirical claims about real companies.

## Current Tables

```text
dim_sales_reps
dim_accounts
fact_leads
```

## Sales Rep Logic

The sales rep table creates coverage for AMER, EMEA, and APJ.

Previously agreed role model:

```text
US territories:
    AMER_ENT
    AMER_MM
    AMER_COMM
    All seller reps are Account Executives.
    Territory determines Enterprise / Mid-Market / Commercial coverage.

LATAM, EMEA, APJ territories:
    First seller rep in each territory is an Enterprise Account Executive.
    Remaining seller reps are Account Executives.

Every territory:
    1 SDR
    1 Regional VP

Every major region:
    1 Area VP for AMER
    1 Area VP for EMEA
    1 Area VP for APJ
```

## Account Logic

The account table creates 2,250 global accounts with region, country, subregion, industry, segment, account fit, territory, and owner assignment.

Account ownership is assigned using `dim_sales_reps`, making non-null account ownership behave like a foreign-key-style relationship:

```text
dim_accounts.owner_rep_id -> dim_sales_reps.rep_id
```

Intentional account data-quality issues already included:

```text
clean
domain_problem_only
intl_no_rep_missing_country
us_no_rep_missing_segmentation
inactive_owner_only
```

## Lead Logic

The lead table creates 12,000 global leads across AMER, EMEA, and APJ.

Lead source distribution already included:

```text
Free Trial / Free Sample
Content Download
Demo Request
Webinar
Paid Search
Partner Referral
Event Scan
Other / Unknown
```

The lead table simulates the real operating problem discussed in the project: many leads provide only limited form data, often just an email address, while other leads provide full profile information.

Current form completeness categories:

```text
email_only
email_name
email_company
email_name_company_title
full_profile
```

Current email quality categories:

```text
business_known_domain
business_unknown_domain
personal_email
education_noncommercial
invalid_fake_email
duplicate_email
disposable_suspicious_domain
```

## Enrichment and Routing Logic

The lead table simulates enrichment from limited data, especially business email domains that may reveal company and country/region.

Current routing model versions:

```text
v1_baseline
v2_domain_inference
v3_logic_fix
```

The routing model is intended to simulate improvement through domain inference and later routing logic fixes.

## Conversion Logic

The current lead generation process creates:

```text
2,800 converted contacts
1,300 converted opportunities
```

Conversion is influenced by lead score, MQL status, first-touch completion, speed-to-lead bucket, lead source, account match status, and random noise.

## Current Dashboard Area Supported

The current v0.1 data supports the first dashboard area:

```text
Leads that do not convert
```

It does not yet create the opportunity or ticket tables needed for the second and third dashboard areas.
