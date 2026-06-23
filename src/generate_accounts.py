"""
Generate a synthetic global account dimension table for a GTM / RevOps portfolio project.

This script creates 2,250 synthetic accounts with controlled global distribution,
segment logic, territory assignment, owner assignment, account fit scoring, and
root-cause-based data-quality issues.

Output:
    data/processed/dim_accounts.csv

Run from the project root:
    python src/generate_accounts.py
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

N_ACCOUNTS = 2250
SEED = 42

REGION_COUNTS = {
    "AMER": 1125,
    "EMEA": 675,
    "APJ": 450,
}

SEGMENT_COUNTS = {
    "Enterprise": 338,
    "Mid-Market": 787,
    "Commercial": 1125,
}

ACCOUNT_SOURCE_COUNTS = {
    "seed_existing": 1800,
    "created_from_converted_lead": 450,
}

DQ_ISSUE_COUNTS = {
    "clean": 1825,
    "us_no_rep_missing_segmentation": 125,
    "intl_no_rep_missing_country": 125,
    "domain_problem_only": 125,
    "inactive_owner_only": 50,
}

DOMAIN_PROBLEM_COUNTS = {
    "missing_domain": 50,
    "duplicate_domain": 40,
    "ambiguous_global_domain": 25,
    "suspicious_domain": 10,
}


COUNTRY_BY_REGION = {
    "AMER": {
        "United States": 0.76,
        "Canada": 0.12,
        "Brazil": 0.07,
        "Mexico": 0.05,
    },
    "EMEA": {
        "United Kingdom": 0.17,
        "Germany": 0.17,
        "France": 0.13,
        "Netherlands": 0.10,
        "Sweden": 0.08,
        "Spain": 0.08,
        "Italy": 0.08,
        "Ireland": 0.07,
        "United Arab Emirates": 0.06,
        "South Africa": 0.06,
    },
    "APJ": {
        "India": 0.225,
        "Japan": 0.20,
        "Australia": 0.175,
        "Singapore": 0.15,
        "South Korea": 0.125,
        "Indonesia": 0.075,
        "New Zealand": 0.05,
    },
}

INDUSTRY_DISTRIBUTION = {
    "Technology": 0.22,
    "Financial Services": 0.14,
    "Healthcare": 0.12,
    "Manufacturing": 0.12,
    "Retail": 0.10,
    "Education": 0.08,
    "Telecommunications": 0.07,
    "Energy": 0.06,
    "Logistics": 0.05,
    "Public Sector": 0.04,
}

EMPLOYEE_BANDS_BY_SEGMENT = {
    "Commercial": {
        "1-50": 0.25,
        "51-200": 0.40,
        "201-500": 0.25,
        "501-1,000": 0.10,
    },
    "Mid-Market": {
        "201-500": 0.25,
        "501-1,000": 0.35,
        "1,001-5,000": 0.35,
        "5,001-10,000": 0.05,
    },
    "Enterprise": {
        "1,001-5,000": 0.30,
        "5,001-10,000": 0.30,
        "10,001+": 0.40,
    },
}

REVENUE_BANDS_BY_SEGMENT = {
    "Commercial": {
        "<$10M": 0.35,
        "$10M-$50M": 0.45,
        "$50M-$250M": 0.20,
    },
    "Mid-Market": {
        "$50M-$250M": 0.40,
        "$250M-$1B": 0.45,
        "$1B-$5B": 0.15,
    },
    "Enterprise": {
        "$250M-$1B": 0.15,
        "$1B-$5B": 0.45,
        "$5B+": 0.40,
    },
}

ACCOUNT_STATUS_DISTRIBUTION = {
    "prospect": 0.60,
    "customer": 0.20,
    "target_account": 0.12,
    "former_customer": 0.05,
    "partner": 0.03,
}

DOMAIN_SUFFIX_BY_COUNTRY = {
    "United States": ".com",
    "Canada": ".ca",
    "Brazil": ".br",
    "Mexico": ".mx",
    "United Kingdom": ".co.uk",
    "Germany": ".de",
    "France": ".fr",
    "Netherlands": ".nl",
    "Sweden": ".se",
    "Spain": ".es",
    "Italy": ".it",
    "Ireland": ".ie",
    "United Arab Emirates": ".ae",
    "South Africa": ".za",
    "India": ".in",
    "Japan": ".co.jp",
    "Australia": ".com.au",
    "Singapore": ".sg",
    "South Korea": ".co.kr",
    "Indonesia": ".co.id",
    "New Zealand": ".co.nz",
}

NAME_PREFIXES = [
    "Northstar", "Blue Harbor", "Ironwood", "Summit", "Redvale",
    "Cobalt", "Silverline", "Evergreen", "Clearpath", "Kestrel",
    "Brightfield", "Atlas", "Crescent", "Vector", "HarborPoint",
    "Stonebridge", "CloudPeak", "Nova", "Pinnacle", "Apex",
    "Terra", "Helio", "Vertex", "Signal", "Quantum",
]

NAME_NOUNS = [
    "Analytics", "Systems", "Software", "Security", "Logistics",
    "Robotics", "Networks", "Health", "Financial", "Manufacturing",
    "Education", "Energy", "Retail", "DataWorks", "Platform",
    "Solutions", "Group", "Labs", "Technologies", "Industries",
]

REPS_BY_TERRITORY = {
    "AMER_ENT": [f"REP_AMER_ENT_{i:02d}" for i in range(1, 9)],
    "AMER_MM": [f"REP_AMER_MM_{i:02d}" for i in range(1, 9)],
    "AMER_COMM": [f"REP_AMER_COMM_{i:02d}" for i in range(1, 9)],
    "LATAM": [f"REP_LATAM_{i:02d}" for i in range(1, 4)],
    "UKI": [f"REP_UKI_{i:02d}" for i in range(1, 4)],
    "DACH": [f"REP_DACH_{i:02d}" for i in range(1, 4)],
    "FR_BENELUX": [f"REP_FRBNLX_{i:02d}" for i in range(1, 4)],
    "NORDICS": [f"REP_NORDICS_{i:02d}" for i in range(1, 3)],
    "SOUTHERN_EUROPE": [f"REP_SEU_{i:02d}" for i in range(1, 3)],
    "MEA": [f"REP_MEA_{i:02d}" for i in range(1, 3)],
    "INDIA": [f"REP_INDIA_{i:02d}" for i in range(1, 4)],
    "JAPAN_KOREA": [f"REP_JPKR_{i:02d}" for i in range(1, 4)],
    "ANZ": [f"REP_ANZ_{i:02d}" for i in range(1, 3)],
    "SEA": [f"REP_SEA_{i:02d}" for i in range(1, 3)],
}


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def make_exact_list(counts: dict[str, int], rng: np.random.Generator) -> list[str]:
    """Create a shuffled list from exact category counts."""
    values = []
    for label, count in counts.items():
        values.extend([label] * count)

    rng.shuffle(values)
    return values


def weighted_choice(options_dict: dict[str, float], rng: np.random.Generator) -> str:
    """Select one value from a weighted dictionary."""
    values = list(options_dict.keys())
    probabilities = list(options_dict.values())
    return str(rng.choice(values, p=probabilities))


def random_dates(
    start_date: str,
    end_date: str,
    n: int,
    rng: np.random.Generator,
) -> list[pd.Timestamp]:
    """Generate n random dates between start_date and end_date, inclusive."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    days_between = (end - start).days
    random_days = rng.integers(0, days_between + 1, size=n)
    return [start + pd.Timedelta(days=int(day)) for day in random_days]


# -----------------------------------------------------------------------------
# Business logic helpers
# -----------------------------------------------------------------------------


def assign_subregion(country: str) -> str:
    mapping = {
        "United States": "North America",
        "Canada": "North America",
        "Brazil": "LATAM",
        "Mexico": "LATAM",
        "United Kingdom": "UKI",
        "Ireland": "UKI",
        "Germany": "DACH",
        "France": "France/Benelux",
        "Netherlands": "France/Benelux",
        "Sweden": "Nordics",
        "Spain": "Southern Europe",
        "Italy": "Southern Europe",
        "United Arab Emirates": "MEA",
        "South Africa": "MEA",
        "India": "India",
        "Japan": "Japan/Korea",
        "South Korea": "Japan/Korea",
        "Australia": "ANZ",
        "New Zealand": "ANZ",
        "Singapore": "SEA",
        "Indonesia": "SEA",
    }
    return mapping[country]


def assign_territory(region: str, subregion: str, segment: str) -> str:
    if region == "AMER":
        if subregion == "LATAM":
            return "LATAM"
        if segment == "Enterprise":
            return "AMER_ENT"
        if segment == "Mid-Market":
            return "AMER_MM"
        return "AMER_COMM"

    if region == "EMEA":
        if subregion == "UKI":
            return "UKI"
        if subregion == "DACH":
            return "DACH"
        if subregion == "France/Benelux":
            return "FR_BENELUX"
        if subregion == "Nordics":
            return "NORDICS"
        if subregion == "Southern Europe":
            return "SOUTHERN_EUROPE"
        return "MEA"

    if region == "APJ":
        if subregion == "India":
            return "INDIA"
        if subregion == "Japan/Korea":
            return "JAPAN_KOREA"
        if subregion == "ANZ":
            return "ANZ"
        return "SEA"

    raise ValueError(f"Unknown region: {region}")


def employee_count_from_band(employee_band: str, rng: np.random.Generator) -> int:
    ranges = {
        "1-50": (1, 50),
        "51-200": (51, 200),
        "201-500": (201, 500),
        "501-1,000": (501, 1000),
        "1,001-5,000": (1001, 5000),
        "5,001-10,000": (5001, 10000),
        "10,001+": (10001, 50000),
    }
    low, high = ranges[employee_band]
    return int(rng.integers(low, high + 1))


def legal_suffix_for_country(country: str, rng: np.random.Generator) -> str:
    suffixes = {
        "United States": ["Inc", "LLC", ""],
        "Canada": ["Inc", "Ltd", ""],
        "United Kingdom": ["Ltd", ""],
        "Ireland": ["Ltd", ""],
        "Germany": ["GmbH", ""],
        "France": ["SAS", ""],
        "Netherlands": ["BV", ""],
        "Sweden": ["AB", ""],
        "Spain": ["SL", ""],
        "Italy": ["SpA", ""],
        "Australia": ["Pty Ltd", ""],
        "New Zealand": ["Ltd", ""],
        "Japan": ["KK", ""],
        "Singapore": ["Pte Ltd", ""],
        "India": ["Pvt Ltd", ""],
        "Brazil": ["Ltda", ""],
        "Mexico": ["SA de CV", ""],
        "South Korea": ["Co Ltd", ""],
        "Indonesia": ["PT", ""],
        "United Arab Emirates": ["LLC", ""],
        "South Africa": ["Pty Ltd", ""],
    }
    return str(rng.choice(suffixes.get(country, [""])))


def generate_account_name(rng: np.random.Generator) -> str:
    prefix = rng.choice(NAME_PREFIXES)
    noun = rng.choice(NAME_NOUNS)
    return f"{prefix} {noun}"


def generate_unique_account_names(n: int, rng: np.random.Generator) -> list[str]:
    names = set()

    while len(names) < n:
        name = generate_account_name(rng)

        if name in names:
            suffix = int(rng.integers(100, 999))
            name = f"{name} {suffix}"

        names.add(name)

    return list(names)


def slugify_company_name(name: str) -> str:
    name = name.lower()
    legal_terms = (
        r"\b(inc|llc|ltd|gmbh|sas|bv|ab|sl|spa|pty ltd|kk|"
        r"pte ltd|pvt ltd|ltda|sa de cv|co ltd|pt)\b"
    )
    name = re.sub(legal_terms, "", name)
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name


def generate_domain(account_name: str, country: str) -> str:
    slug = slugify_company_name(account_name)
    suffix = DOMAIN_SUFFIX_BY_COUNTRY[country]
    return f"{slug}{suffix}"


def convert_to_ambiguous_com_domain(domain: str) -> str:
    """Convert a country-specific domain into a .com domain to simulate ambiguity."""
    if pd.isna(domain):
        return domain

    domain = str(domain)
    for suffix in sorted(DOMAIN_SUFFIX_BY_COUNTRY.values(), key=len, reverse=True):
        if domain.endswith(suffix):
            return f"{domain[: -len(suffix)]}.com"

    return domain


def calculate_account_fit_score(
    segment: str,
    industry: str,
    account_status: str,
    rng: np.random.Generator,
) -> int:
    score = 50

    if segment == "Enterprise":
        score += 15
    elif segment == "Mid-Market":
        score += 8

    if industry in ["Technology", "Financial Services", "Healthcare", "Telecommunications"]:
        score += 12
    elif industry in ["Manufacturing", "Logistics", "Energy"]:
        score += 6

    if account_status == "target_account":
        score += 10
    elif account_status == "customer":
        score += 5
    elif account_status == "former_customer":
        score -= 5

    score += rng.normal(0, 8)
    return int(np.clip(round(score), 0, 100))


def fit_tier(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def calculate_data_quality_score(row: pd.Series) -> int:
    """Score account data quality from 0 to 100."""
    score = 0
    domain_quality = row["domain_quality"]

    # Domain quality: max 20
    if pd.isna(row["account_domain"]) or domain_quality == "missing_domain":
        score += 0
    elif domain_quality == "suspicious_domain":
        score += 5
    elif domain_quality == "duplicate_domain":
        score += 10
    elif domain_quality == "ambiguous_global_domain":
        score += 15
    elif domain_quality == "valid_business_domain":
        score += 20

    # Country supports region and territory inference: max 15
    if pd.notna(row["country"]):
        score += 15

    # Territory assignment: max 20
    if pd.notna(row["territory_id"]):
        score += 20

    # Active owner assignment: max 20
    if pd.notna(row["owner_rep_id"]) and row["owner_rep_id"] != "INACTIVE_REP":
        score += 20

    # Firmographic completeness: max 25
    if pd.notna(row["industry"]):
        score += 10
    if pd.notna(row["segment"]):
        score += 10
    if pd.notna(row["estimated_employee_count"]):
        score += 5

    return score


def data_quality_tier(score: int) -> str:
    if score == 100:
        return "excellent"
    if score >= 85:
        return "good"
    if score >= 70:
        return "partial"
    return "poor"


# -----------------------------------------------------------------------------
# Data-quality issue injection
# -----------------------------------------------------------------------------


def inject_account_dq_issues(
    accounts: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Inject controlled, root-cause-based data-quality issues.

    The goal is to create realistic issue clusters rather than isolated random
    nulls. This supports later dashboard analysis around routing failure,
    territory assignment, account matching, and data remediation.
    """
    accounts = accounts.copy()

    accounts["account_issue_type"] = "clean"
    accounts["account_dq_root_cause"] = "none"
    accounts["domain_quality"] = "valid_business_domain"

    # 1. US accounts where missing segmentation prevents territory/rep assignment.
    us_pool = accounts[accounts["country"] == "United States"].index.to_numpy()
    us_issue_idx = rng.choice(
        us_pool,
        size=DQ_ISSUE_COUNTS["us_no_rep_missing_segmentation"],
        replace=False,
    )

    accounts.loc[us_issue_idx, "account_issue_type"] = "us_no_rep_missing_segmentation"
    accounts.loc[us_issue_idx, "account_dq_root_cause"] = (
        "missing_employee_count_and_segment_prevented_territory_assignment"
    )
    accounts.loc[us_issue_idx, "estimated_employee_count"] = pd.NA
    accounts.loc[us_issue_idx, "employee_band"] = pd.NA
    accounts.loc[us_issue_idx, "annual_revenue_band"] = pd.NA
    accounts.loc[us_issue_idx, "segment"] = pd.NA
    accounts.loc[us_issue_idx, "territory_id"] = pd.NA
    accounts.loc[us_issue_idx, "owner_rep_id"] = pd.NA

    # 2. International accounts where missing country prevents territory/rep assignment.
    non_us_pool = accounts[
        (accounts["country"] != "United States")
        & (~accounts.index.isin(us_issue_idx))
    ].index.to_numpy()
    intl_issue_idx = rng.choice(
        non_us_pool,
        size=DQ_ISSUE_COUNTS["intl_no_rep_missing_country"],
        replace=False,
    )

    accounts.loc[intl_issue_idx, "account_issue_type"] = "intl_no_rep_missing_country"
    accounts.loc[intl_issue_idx, "account_dq_root_cause"] = (
        "missing_country_prevented_region_and_territory_assignment"
    )
    accounts.loc[intl_issue_idx, "country"] = pd.NA
    accounts.loc[intl_issue_idx, "subregion"] = pd.NA
    accounts.loc[intl_issue_idx, "region"] = pd.NA
    accounts.loc[intl_issue_idx, "territory_id"] = pd.NA
    accounts.loc[intl_issue_idx, "owner_rep_id"] = pd.NA

    used_idx = set(us_issue_idx).union(set(intl_issue_idx))

    # 3. Domain problems that affect lead-to-account matching but not ownership.
    remaining_pool = accounts[~accounts.index.isin(used_idx)].index.to_numpy()
    domain_issue_idx = rng.choice(
        remaining_pool,
        size=DQ_ISSUE_COUNTS["domain_problem_only"],
        replace=False,
    )

    domain_problem_labels = make_exact_list(DOMAIN_PROBLEM_COUNTS, rng)
    accounts.loc[domain_issue_idx, "account_issue_type"] = "domain_problem_only"
    accounts.loc[domain_issue_idx, "account_dq_root_cause"] = (
        "domain_quality_issue_affects_lead_to_account_matching"
    )

    for idx, domain_problem in zip(domain_issue_idx, domain_problem_labels):
        accounts.loc[idx, "domain_quality"] = domain_problem

        if domain_problem == "missing_domain":
            accounts.loc[idx, "account_domain"] = pd.NA

        elif domain_problem == "duplicate_domain":
            valid_domain_pool = accounts.loc[
                (accounts["account_domain"].notna()) & (accounts.index != idx),
                "account_domain",
            ]
            accounts.loc[idx, "account_domain"] = rng.choice(valid_domain_pool.to_numpy())

        elif domain_problem == "ambiguous_global_domain":
            accounts.loc[idx, "account_domain"] = convert_to_ambiguous_com_domain(
                accounts.loc[idx, "account_domain"]
            )

        elif domain_problem == "suspicious_domain":
            accounts.loc[idx, "account_domain"] = f"unknown-{idx}.xyz"

    used_idx = used_idx.union(set(domain_issue_idx))

    # 4. Accounts with territory present but inactive owner assignment.
    remaining_pool = accounts[~accounts.index.isin(used_idx)].index.to_numpy()
    inactive_owner_idx = rng.choice(
        remaining_pool,
        size=DQ_ISSUE_COUNTS["inactive_owner_only"],
        replace=False,
    )

    accounts.loc[inactive_owner_idx, "account_issue_type"] = "inactive_owner_only"
    accounts.loc[inactive_owner_idx, "account_dq_root_cause"] = (
        "assigned_owner_inactive_after_territory_assignment"
    )
    accounts.loc[inactive_owner_idx, "owner_rep_id"] = "INACTIVE_REP"

    return accounts


# -----------------------------------------------------------------------------
# Main build steps
# -----------------------------------------------------------------------------


def build_accounts(seed: int = SEED) -> pd.DataFrame:
    """Build the full synthetic account dimension table."""
    rng = np.random.default_rng(seed)

    account_ids = [f"ACC_{i:06d}" for i in range(1, N_ACCOUNTS + 1)]
    regions = make_exact_list(REGION_COUNTS, rng)
    segments = make_exact_list(SEGMENT_COUNTS, rng)
    account_created_sources = make_exact_list(ACCOUNT_SOURCE_COUNTS, rng)

    countries = [weighted_choice(COUNTRY_BY_REGION[region], rng) for region in regions]
    subregions = [assign_subregion(country) for country in countries]
    industries = [weighted_choice(INDUSTRY_DISTRIBUTION, rng) for _ in range(N_ACCOUNTS)]

    employee_bands = [
        weighted_choice(EMPLOYEE_BANDS_BY_SEGMENT[segment], rng)
        for segment in segments
    ]
    estimated_employee_counts = [
        employee_count_from_band(band, rng)
        for band in employee_bands
    ]
    revenue_bands = [
        weighted_choice(REVENUE_BANDS_BY_SEGMENT[segment], rng)
        for segment in segments
    ]

    raw_names = generate_unique_account_names(N_ACCOUNTS, rng)
    account_names = []
    for name, country in zip(raw_names, countries):
        suffix = legal_suffix_for_country(country, rng)
        account_names.append(f"{name} {suffix}" if suffix else name)

    domains = [
        generate_domain(name, country)
        for name, country in zip(account_names, countries)
    ]

    account_statuses = [
        weighted_choice(ACCOUNT_STATUS_DISTRIBUTION, rng)
        for _ in range(N_ACCOUNTS)
    ]
    territory_ids = [
        assign_territory(region, subregion, segment)
        for region, subregion, segment in zip(regions, subregions, segments)
    ]
    owner_rep_ids = [
        rng.choice(REPS_BY_TERRITORY[territory])
        for territory in territory_ids
    ]

    account_fit_scores = [
        calculate_account_fit_score(segment, industry, status, rng)
        for segment, industry, status
        in zip(segments, industries, account_statuses)
    ]
    account_fit_tiers = [fit_tier(score) for score in account_fit_scores]
    created_dates = random_dates("2023-01-01", "2025-12-31", N_ACCOUNTS, rng)

    accounts = pd.DataFrame({
        "account_id": account_ids,
        "account_name": account_names,
        "account_domain": domains,
        "account_created_source": account_created_sources,
        "account_status": account_statuses,
        "industry": industries,
        "segment": segments,
        "employee_band": employee_bands,
        "estimated_employee_count": estimated_employee_counts,
        "annual_revenue_band": revenue_bands,
        "country": countries,
        "subregion": subregions,
        "region": regions,
        "territory_id": territory_ids,
        "owner_rep_id": owner_rep_ids,
        "account_fit_score": account_fit_scores,
        "account_fit_tier": account_fit_tiers,
        "created_date": created_dates,
    })

    accounts = inject_account_dq_issues(accounts, rng)
    accounts["data_quality_score"] = accounts.apply(calculate_data_quality_score, axis=1)
    accounts["data_quality_tier"] = accounts["data_quality_score"].apply(data_quality_tier)

    accounts["estimated_employee_count"] = accounts["estimated_employee_count"].astype("Int64")
    accounts["created_date"] = pd.to_datetime(accounts["created_date"]).dt.date

    # Keep columns in a business-readable order.
    column_order = [
        "account_id",
        "account_name",
        "account_domain",
        "account_created_source",
        "account_status",
        "industry",
        "segment",
        "employee_band",
        "estimated_employee_count",
        "annual_revenue_band",
        "country",
        "subregion",
        "region",
        "territory_id",
        "owner_rep_id",
        "account_fit_score",
        "account_fit_tier",
        "data_quality_score",
        "data_quality_tier",
        "domain_quality",
        "account_issue_type",
        "account_dq_root_cause",
        "created_date",
    ]

    return accounts[column_order]


# -----------------------------------------------------------------------------
# Validation and output
# -----------------------------------------------------------------------------


def validate_accounts(accounts: pd.DataFrame) -> None:
    """Print basic validation checks for the generated account table."""
    print("Total accounts:", len(accounts))

    print("\nRegion counts:")
    print(accounts["region"].value_counts(dropna=False))

    print("\nSegment counts:")
    print(accounts["segment"].value_counts(dropna=False))

    print("\nAccount source counts:")
    print(accounts["account_created_source"].value_counts(dropna=False))

    print("\nAccount issue type counts:")
    print(accounts["account_issue_type"].value_counts(dropna=False))

    print("\nDQ root cause counts:")
    print(accounts["account_dq_root_cause"].value_counts(dropna=False))

    print("\nData quality score counts:")
    print(accounts["data_quality_score"].value_counts().sort_index())

    print("\nData quality tier counts:")
    print(accounts["data_quality_tier"].value_counts(dropna=False))

    print("\nDomain quality counts:")
    print(accounts["domain_quality"].value_counts(dropna=False))

    print("\nMissing field rates:")
    missing_rates = accounts[[
        "account_domain",
        "country",
        "region",
        "segment",
        "territory_id",
        "owner_rep_id",
        "estimated_employee_count",
    ]].isna().mean().round(3)
    print(missing_rates)

    print("\nDuplicate non-null domain count:")
    print(accounts["account_domain"].dropna().duplicated().sum())


def save_accounts(accounts: pd.DataFrame) -> Path:
    """Save accounts to the processed data folder."""
    output_path = Path("data/processed")
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "dim_accounts.csv"
    accounts.to_csv(output_file, index=False)
    print(f"\nSaved accounts to: {output_file}")

    return output_file


if __name__ == "__main__":
    accounts_df = build_accounts()
    validate_accounts(accounts_df)
    save_accounts(accounts_df)
