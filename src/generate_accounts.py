"""
Generate a synthetic global account dimension table for a GTM / RevOps portfolio project.

This linked version assigns account owner_rep_id values from dim_sales_reps.csv
instead of using an embedded territory-to-rep dictionary. That makes account owner
assignments behave like a real foreign-key-style relationship:

    dim_accounts.owner_rep_id -> dim_sales_reps.rep_id

Intentional account data-quality issues are preserved. Accounts that cannot have a
valid current owner because of missing segmentation, missing country, or inactive
owner cleanup keep owner_rep_id blank and use account_issue_type / account_dq_root_cause
to explain the root cause.

Inputs:
    data/processed/dim_sales_reps.csv

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

SALES_REPS_INPUT_CANDIDATES = [
    Path("data/processed/dim_sales_reps.csv"),
    Path("data/raw/dim_sales_reps.csv"),
    Path("dim_sales_reps.csv"),
]

OUTPUT_FILE = Path("data/processed/dim_accounts.csv")

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

US_SEGMENT_TERRITORIES = {"AMER_ENT", "AMER_MM", "AMER_COMM"}
SELLER_ROLES = {"Account Executive", "Enterprise Account Executive"}

REQUIRED_SALES_REP_COLUMNS = {
    "rep_id",
    "region",
    "territory_id",
    "role",
    "active_flag",
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
# Sales-rep foreign-key helpers
# -----------------------------------------------------------------------------


def load_sales_reps() -> pd.DataFrame:
    """Load dim_sales_reps.csv from the project data folders."""
    for path in SALES_REPS_INPUT_CANDIDATES:
        if path.exists():
            reps = pd.read_csv(path)
            missing = REQUIRED_SALES_REP_COLUMNS - set(reps.columns)
            if missing:
                raise ValueError(
                    f"Sales reps file {path} is missing required columns: {sorted(missing)}"
                )
            print(f"Loaded sales reps from: {path}")
            return reps

    searched = ", ".join(str(path) for path in SALES_REPS_INPUT_CANDIDATES)
    raise FileNotFoundError(
        "Could not find dim_sales_reps.csv. Searched: " + searched
    )


def eligible_account_owners(sales_reps: pd.DataFrame) -> pd.DataFrame:
    """Return active quota-carrying reps eligible to own accounts."""
    owners = sales_reps[
        sales_reps["role"].isin(SELLER_ROLES)
        & (sales_reps["active_flag"] == 1)
        & sales_reps["territory_id"].notna()
        & sales_reps["rep_id"].notna()
    ].copy()

    if owners.empty:
        raise ValueError("No active seller reps found in dim_sales_reps.csv.")

    return owners


def choose_owner_rep_id(
    territory_id: str,
    segment: str,
    account_owners: pd.DataFrame,
    rng: np.random.Generator,
) -> str:
    """
    Choose an account owner from dim_sales_reps.

    Business rule:
    - US segment territories use Account Executives only because the territory
      determines Enterprise / Mid-Market / Commercial coverage.
    - LATAM, EMEA, and APJ Enterprise accounts prefer Enterprise AEs.
    - LATAM, EMEA, and APJ Mid-Market / Commercial accounts prefer AEs.
    """
    territory_reps = account_owners[account_owners["territory_id"] == territory_id]

    if territory_reps.empty:
        raise ValueError(f"No active seller reps found for territory_id: {territory_id}")

    if territory_id in US_SEGMENT_TERRITORIES:
        candidates = territory_reps[territory_reps["role"] == "Account Executive"]
    elif segment == "Enterprise":
        candidates = territory_reps[territory_reps["role"] == "Enterprise Account Executive"]
        if candidates.empty:
            candidates = territory_reps[territory_reps["role"] == "Account Executive"]
    else:
        candidates = territory_reps[territory_reps["role"] == "Account Executive"]
        if candidates.empty:
            candidates = territory_reps[territory_reps["role"] == "Enterprise Account Executive"]

    if candidates.empty:
        raise ValueError(
            f"No eligible owner candidates found for territory={territory_id}, segment={segment}"
        )

    return str(rng.choice(candidates["rep_id"].to_numpy()))


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
    """Generate unique fake account names in deterministic insertion order."""
    names = []
    seen_names = set()

    while len(names) < n:
        name = generate_account_name(rng)

        if name in seen_names:
            suffix = int(rng.integers(100, 999))
            name = f"{name} {suffix}"

        if name not in seen_names:
            seen_names.add(name)
            names.append(name)

    return names


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

    # Active current owner assignment: max 20
    if pd.notna(row["owner_rep_id"]):
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

    owner_rep_id remains a foreign-key-compatible field: every non-null value
    should exist in dim_sales_reps.rep_id. Accounts with no valid current owner
    have owner_rep_id left blank and the root cause stored in account_dq_root_cause.
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

    # 4. Accounts where a prior owner is no longer active and cleanup is needed.
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
    accounts.loc[inactive_owner_idx, "owner_rep_id"] = pd.NA

    return accounts


# -----------------------------------------------------------------------------
# Main build steps
# -----------------------------------------------------------------------------


def build_accounts(seed: int = SEED) -> pd.DataFrame:
    """Build the full synthetic account dimension table."""
    rng = np.random.default_rng(seed)

    sales_reps = load_sales_reps()
    account_owners = eligible_account_owners(sales_reps)

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
        choose_owner_rep_id(territory, segment, account_owners, rng)
        for territory, segment in zip(territory_ids, segments)
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


def validate_account_owner_foreign_keys(accounts: pd.DataFrame, sales_reps: pd.DataFrame) -> None:
    """Validate dim_accounts.owner_rep_id against dim_sales_reps.rep_id."""
    owner_ids = set(accounts["owner_rep_id"].dropna().astype(str).unique())
    rep_ids = set(sales_reps["rep_id"].astype(str).unique())
    missing_ids = sorted(owner_ids - rep_ids)

    if missing_ids:
        raise ValueError(
            "owner_rep_id values missing from dim_sales_reps.rep_id: "
            f"{missing_ids[:20]}"
        )

    owner_rows = accounts[accounts["owner_rep_id"].notna()].merge(
        sales_reps[["rep_id", "territory_id", "role", "active_flag"]],
        left_on="owner_rep_id",
        right_on="rep_id",
        how="left",
        suffixes=("_account", "_rep"),
    )

    non_seller_owners = owner_rows[~owner_rows["role"].isin(SELLER_ROLES)]
    if not non_seller_owners.empty:
        bad_roles = sorted(non_seller_owners["role"].dropna().unique().tolist())
        raise ValueError(f"Accounts assigned to non-seller roles: {bad_roles}")

    inactive_owners = owner_rows[owner_rows["active_flag"] != 1]
    if not inactive_owners.empty:
        raise ValueError("Accounts assigned to inactive reps in dim_sales_reps.")

    territory_mismatch = owner_rows[
        owner_rows["territory_id_account"] != owner_rows["territory_id_rep"]
    ]
    if not territory_mismatch.empty:
        preview = territory_mismatch[[
            "account_id", "territory_id_account", "owner_rep_id", "territory_id_rep"
        ]].head(10)
        raise ValueError(
            "Account owner territory mismatches found:\n" + preview.to_string(index=False)
        )


def validate_accounts(accounts: pd.DataFrame) -> None:
    """Print basic validation checks for the generated account table."""
    sales_reps = load_sales_reps()
    validate_account_owner_foreign_keys(accounts, sales_reps)

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

    print("\nAccount-owner FK validation:")
    print("Passed: every non-null owner_rep_id exists in dim_sales_reps and matches territory.")


def save_accounts(accounts: pd.DataFrame) -> Path:
    """Save accounts to the processed data folder."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    accounts.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved accounts to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    accounts_df = build_accounts()
    validate_accounts(accounts_df)
    save_accounts(accounts_df)
