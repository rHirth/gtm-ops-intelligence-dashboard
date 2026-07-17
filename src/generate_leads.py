"""
Generate a synthetic lead fact table for a GTM / RevOps portfolio project.

This script creates fact_leads.csv using the existing dim_accounts.csv and
 dim_sales_reps.csv files when available. The goal is to simulate a realistic
 global lead pool where lead source, form completeness, email quality, enrichment,
 routing, speed-to-lead, and conversion are connected by explicit business logic.

Output:
    data/processed/fact_leads.csv

Run from the project root:
    python src/generate_leads.py
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

N_LEADS = 12_000
SEED = 42
OUTPUT_FILE = Path("data/processed/fact_leads.csv")

ACCOUNT_INPUT_CANDIDATES = [
    Path("data/processed/dim_accounts.csv"),
    Path("data/raw/dim_accounts.csv"),
    Path("data/raw/accounts.csv"),
    Path("dim_accounts.csv"),
]

SALES_REP_INPUT_CANDIDATES = [
    Path("data/processed/dim_sales_reps.csv"),
    Path("data/raw/dim_sales_reps.csv"),
    Path("dim_sales_reps.csv"),
]

LEAD_SOURCE_COUNTS = {
    "Free Trial / Free Sample": 3000,
    "Content Download": 2400,
    "Demo Request": 1800,
    "Webinar": 1800,
    "Paid Search": 1200,
    "Partner Referral": 840,
    "Event Scan": 600,
    "Other / Unknown": 360,
}

REGION_COUNTS = {
    "AMER": 6000,
    "EMEA": 3600,
    "APJ": 2400,
}

ACCOUNT_MATCH_COUNTS = {
    "existing_account_match": 4800,
    "new_account_candidate": 3000,
    "partial_fuzzy_match": 1440,
    "no_account_match": 1200,
    "personal_invalid_no_match": 1200,
    "duplicate_existing_lead_contact": 360,
}

FORM_COMPLETENESS_WEIGHTS = {
    "email_only": 0.35,
    "email_name": 0.20,
    "email_company": 0.15,
    "email_name_company_title": 0.20,
    "full_profile": 0.10,
}

EMAIL_TYPE_WEIGHTS = {
    "business_known_domain": 0.45,
    "business_unknown_domain": 0.20,
    "personal_email": 0.15,
    "education_noncommercial": 0.05,
    "invalid_fake_email": 0.07,
    "duplicate_email": 0.03,
    "disposable_suspicious_domain": 0.05,
}

JOB_FUNCTION_WEIGHTS = {
    "IT / Engineering": 0.24,
    "Security / Compliance": 0.12,
    "Operations": 0.12,
    "Sales / Revenue": 0.10,
    "Marketing": 0.08,
    "Finance / Procurement": 0.08,
    "Executive / Founder": 0.07,
    "Product / Data": 0.07,
    "Student / Researcher": 0.05,
    "Unknown": 0.07,
}

SENIORITY_WEIGHTS = {
    "Executive / C-level": 0.05,
    "VP / Head of": 0.08,
    "Director": 0.14,
    "Manager": 0.22,
    "Individual Contributor": 0.28,
    "Consultant / Contractor": 0.07,
    "Student / Personal Use": 0.05,
    "Unknown": 0.11,
}

COUNTRY_BY_REGION = {
    "AMER": {
        "United States": 0.78,
        "Canada": 0.10,
        "Brazil": 0.07,
        "Mexico": 0.05,
    },
    "EMEA": {
        "United Kingdom": 0.16,
        "Germany": 0.16,
        "France": 0.12,
        "Netherlands": 0.10,
        "Sweden": 0.08,
        "Spain": 0.08,
        "Italy": 0.08,
        "Ireland": 0.07,
        "United Arab Emirates": 0.07,
        "South Africa": 0.08,
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

PERSONAL_EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"]
EDU_EMAIL_DOMAINS = ["stanford.edu", "berkeley.edu", "sfsu.edu", "mit.edu", "ox.ac.uk"]
DISPOSABLE_DOMAINS = ["maildrop.cc", "tempmail.net", "unknown-lead.xyz", "trial-user.xyz"]
INVALID_EMAIL_PATTERNS = ["test@test", "asdf@example", "none@none", "fake@fake", "noemail@unknown"]

SELLER_ROLES = {"Account Executive", "Enterprise Account Executive", "Sales Development Representative"}
US_SEGMENT_TERRITORIES = {"AMER_ENT", "AMER_MM", "AMER_COMM"}

EXPECTED_COLUMNS = [
    "lead_id",
    "created_at",
    "created_month",
    "created_quarter",
    "routing_model_version",
    "lead_source",
    "region",
    "subregion",
    "country",
    "segment",
    "industry",
    "email",
    "email_domain",
    "email_type",
    "form_completeness",
    "full_name_provided",
    "company_name_provided",
    "job_title_provided",
    "country_provided",
    "inferred_company",
    "inferred_country",
    "inferred_region",
    "account_match_status",
    "matched_account_id",
    "possible_account_id",
    "created_account_id",
    "created_contact_id",
    "job_function",
    "seniority",
    "lead_score",
    "lead_score_band",
    "mql_flag",
    "enrichment_status",
    "enrichment_confidence_score",
    "missing_required_fields_count",
    "routing_status",
    "routing_failure_reason",
    "assignment_method",
    "assigned_rep_id",
    "assigned_territory_id",
    "minutes_to_assignment",
    "first_touch_at",
    "minutes_to_first_touch",
    "speed_to_lead_bucket",
    "first_touch_completed",
    "converted_to_contact",
    "converted_to_account",
    "converted_to_opportunity",
    "created_opportunity_id",
    "conversion_outcome",
    "non_conversion_reason",
    "data_quality_score",
    "data_quality_tier",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def make_exact_list(counts: dict[str, int], rng: np.random.Generator) -> list[str]:
    """Create a shuffled list from exact category counts."""
    values: list[str] = []
    for label, count in counts.items():
        values.extend([label] * count)

    if len(values) != N_LEADS:
        raise ValueError(f"Counts must sum to {N_LEADS}; received {len(values)}")

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


def clean_domain(domain: Any) -> str | None:
    """Normalize domain values read from account data."""
    if pd.isna(domain):
        return None
    return str(domain).strip().lower()


def domain_to_company(domain: str | None) -> str | pd.NA:
    """Create a simple inferred company name from a domain."""
    if domain is None or pd.isna(domain):
        return pd.NA

    first_part = str(domain).split(".")[0]
    first_part = re.sub(r"[^a-zA-Z0-9]+", " ", first_part)
    first_part = re.sub(r"\d+", "", first_part).strip()

    if not first_part:
        return pd.NA

    return first_part.title()


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
    """Mirror the account territory assignment logic."""
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


def load_first_available(candidates: list[Path], label: str) -> tuple[pd.DataFrame, Path]:
    """Load the first existing CSV from a list of candidate paths."""
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            print(f"Loaded {label} from: {path}")
            return df, path

    raise FileNotFoundError(
        f"Could not find {label}. Tried: {[str(path) for path in candidates]}"
    )


# -----------------------------------------------------------------------------
# Lead attribute logic
# -----------------------------------------------------------------------------


def routing_model_version(created_at: pd.Timestamp) -> str:
    """Simulate a staged lead-routing improvement program."""
    if created_at < pd.Timestamp("2024-07-01"):
        return "v1_baseline"
    if created_at < pd.Timestamp("2025-01-01"):
        return "v2_domain_inference"
    return "v3_logic_fix"


def choose_source_adjusted_form_completeness(source: str, rng: np.random.Generator) -> str:
    """Pick form completeness with source-specific behavior."""
    weights = FORM_COMPLETENESS_WEIGHTS.copy()

    if source == "Free Trial / Free Sample":
        weights = {
            "email_only": 0.52,
            "email_name": 0.20,
            "email_company": 0.12,
            "email_name_company_title": 0.12,
            "full_profile": 0.04,
        }
    elif source == "Demo Request":
        weights = {
            "email_only": 0.12,
            "email_name": 0.14,
            "email_company": 0.18,
            "email_name_company_title": 0.34,
            "full_profile": 0.22,
        }
    elif source == "Partner Referral":
        weights = {
            "email_only": 0.10,
            "email_name": 0.15,
            "email_company": 0.20,
            "email_name_company_title": 0.35,
            "full_profile": 0.20,
        }
    elif source == "Content Download":
        weights = {
            "email_only": 0.48,
            "email_name": 0.22,
            "email_company": 0.12,
            "email_name_company_title": 0.14,
            "full_profile": 0.04,
        }

    return weighted_choice(weights, rng)


def choose_email_type(account_match_status: str, source: str, rng: np.random.Generator) -> str:
    """Pick email type using account-match status and source-specific behavior."""
    if account_match_status == "existing_account_match":
        weights = {
            "business_known_domain": 0.82,
            "business_unknown_domain": 0.10,
            "personal_email": 0.03,
            "education_noncommercial": 0.01,
            "invalid_fake_email": 0.00,
            "duplicate_email": 0.02,
            "disposable_suspicious_domain": 0.02,
        }
    elif account_match_status == "new_account_candidate":
        weights = {
            "business_known_domain": 0.30,
            "business_unknown_domain": 0.50,
            "personal_email": 0.08,
            "education_noncommercial": 0.02,
            "invalid_fake_email": 0.01,
            "duplicate_email": 0.01,
            "disposable_suspicious_domain": 0.08,
        }
    elif account_match_status == "partial_fuzzy_match":
        weights = {
            "business_known_domain": 0.30,
            "business_unknown_domain": 0.32,
            "personal_email": 0.12,
            "education_noncommercial": 0.03,
            "invalid_fake_email": 0.03,
            "duplicate_email": 0.10,
            "disposable_suspicious_domain": 0.10,
        }
    elif account_match_status == "duplicate_existing_lead_contact":
        weights = {
            "business_known_domain": 0.55,
            "business_unknown_domain": 0.10,
            "personal_email": 0.07,
            "education_noncommercial": 0.01,
            "invalid_fake_email": 0.00,
            "duplicate_email": 0.25,
            "disposable_suspicious_domain": 0.02,
        }
    elif account_match_status == "personal_invalid_no_match":
        weights = {
            "business_known_domain": 0.00,
            "business_unknown_domain": 0.02,
            "personal_email": 0.50,
            "education_noncommercial": 0.12,
            "invalid_fake_email": 0.25,
            "duplicate_email": 0.02,
            "disposable_suspicious_domain": 0.09,
        }
    else:
        weights = {
            "business_known_domain": 0.12,
            "business_unknown_domain": 0.35,
            "personal_email": 0.20,
            "education_noncommercial": 0.07,
            "invalid_fake_email": 0.12,
            "duplicate_email": 0.04,
            "disposable_suspicious_domain": 0.10,
        }

    if source == "Free Trial / Free Sample":
        weights["personal_email"] += 0.04
        weights["invalid_fake_email"] += 0.03
        weights["business_known_domain"] = max(0, weights["business_known_domain"] - 0.04)
        weights["business_unknown_domain"] = max(0, weights["business_unknown_domain"] - 0.03)

    total = sum(weights.values())
    weights = {key: value / total for key, value in weights.items()}
    return weighted_choice(weights, rng)


def choose_segment(account_row: pd.Series | None, source: str, rng: np.random.Generator) -> str:
    """Use account segment when available, otherwise generate a plausible segment."""
    if account_row is not None and pd.notna(account_row.get("segment")):
        return str(account_row["segment"])

    weights = {
        "Enterprise": 0.18,
        "Mid-Market": 0.32,
        "Commercial": 0.35,
        "SMB": 0.15,
    }

    if source == "Demo Request":
        weights = {"Enterprise": 0.25, "Mid-Market": 0.35, "Commercial": 0.30, "SMB": 0.10}
    elif source in {"Free Trial / Free Sample", "Content Download"}:
        weights = {"Enterprise": 0.12, "Mid-Market": 0.26, "Commercial": 0.40, "SMB": 0.22}
    elif source == "Partner Referral":
        weights = {"Enterprise": 0.30, "Mid-Market": 0.35, "Commercial": 0.25, "SMB": 0.10}

    return weighted_choice(weights, rng)


def choose_job_function(source: str, rng: np.random.Generator) -> str:
    """Choose job function with source-specific skews."""
    weights = JOB_FUNCTION_WEIGHTS.copy()

    if source == "Demo Request":
        weights["Executive / Founder"] += 0.04
        weights["Operations"] += 0.04
        weights["IT / Engineering"] += 0.03
        weights["Student / Researcher"] = max(0.01, weights["Student / Researcher"] - 0.03)
    elif source == "Content Download":
        weights["Marketing"] += 0.05
        weights["Product / Data"] += 0.04
        weights["Student / Researcher"] += 0.03
        weights["Executive / Founder"] = max(0.02, weights["Executive / Founder"] - 0.03)
    elif source == "Free Trial / Free Sample":
        weights["IT / Engineering"] += 0.07
        weights["Student / Researcher"] += 0.03
        weights["Unknown"] += 0.03
    elif source == "Partner Referral":
        weights["Executive / Founder"] += 0.05
        weights["Finance / Procurement"] += 0.04
        weights["Operations"] += 0.03

    total = sum(weights.values())
    weights = {key: value / total for key, value in weights.items()}
    return weighted_choice(weights, rng)


def choose_seniority(job_function: str, source: str, rng: np.random.Generator) -> str:
    """Choose seniority with source and job-function adjustments."""
    weights = SENIORITY_WEIGHTS.copy()

    if job_function == "Executive / Founder":
        weights = {
            "Executive / C-level": 0.40,
            "VP / Head of": 0.25,
            "Director": 0.15,
            "Manager": 0.08,
            "Individual Contributor": 0.04,
            "Consultant / Contractor": 0.03,
            "Student / Personal Use": 0.00,
            "Unknown": 0.05,
        }
    elif job_function == "Student / Researcher":
        weights = {
            "Executive / C-level": 0.00,
            "VP / Head of": 0.01,
            "Director": 0.02,
            "Manager": 0.04,
            "Individual Contributor": 0.18,
            "Consultant / Contractor": 0.05,
            "Student / Personal Use": 0.58,
            "Unknown": 0.12,
        }
    elif source == "Demo Request":
        weights["VP / Head of"] += 0.04
        weights["Director"] += 0.05
        weights["Manager"] += 0.03
        weights["Unknown"] = max(0.04, weights["Unknown"] - 0.05)

    total = sum(weights.values())
    weights = {key: value / total for key, value in weights.items()}
    return weighted_choice(weights, rng)


def lead_score_band(score: int) -> str:
    if score >= 85:
        return "85-100 Excellent fit"
    if score >= 70:
        return "70-84 Strong fit"
    if score >= 50:
        return "50-69 Moderate fit"
    if score >= 25:
        return "25-49 Low fit"
    return "0-24 Poor fit"


def speed_bucket(minutes: float | pd.NA) -> str:
    if pd.isna(minutes):
        return "No touch"
    if minutes <= 15:
        return "0-15 minutes"
    if minutes <= 60:
        return "16-60 minutes"
    if minutes <= 240:
        return "1-4 hours"
    if minutes <= 1440:
        return "Same day"
    if minutes <= 4320:
        return "1-3 days"
    return "4+ days"



def choose_source_response_delay(source: str, rng: np.random.Generator) -> int:
    """Generate source-specific rep response delay after assignment."""
    draw = rng.random()

    if source == "Demo Request":
        if draw < 0.70:
            return int(rng.integers(1, 8))
        if draw < 0.92:
            return int(rng.integers(8, 45))
        return int(rng.integers(45, 180))

    if source == "Partner Referral":
        if draw < 0.50:
            return int(rng.integers(2, 12))
        if draw < 0.82:
            return int(rng.integers(20, 90))
        return int(rng.integers(90, 480))

    if source == "Paid Search":
        if draw < 0.42:
            return int(rng.integers(2, 15))
        if draw < 0.78:
            return int(rng.integers(25, 120))
        return int(rng.integers(120, 720))

    if source == "Free Trial / Free Sample":
        if draw < 0.35:
            return int(rng.integers(2, 18))
        if draw < 0.70:
            return int(rng.integers(25, 180))
        return int(rng.integers(180, 1440))

    if source == "Webinar":
        if draw < 0.15:
            return int(rng.integers(10, 45))
        if draw < 0.55:
            return int(rng.integers(45, 240))
        return int(rng.integers(240, 1440))

    if source == "Event Scan":
        if draw < 0.10:
            return int(rng.integers(30, 120))
        if draw < 0.45:
            return int(rng.integers(120, 720))
        return int(rng.integers(720, 2880))

    if source == "Content Download":
        if draw < 0.06:
            return int(rng.integers(30, 120))
        if draw < 0.36:
            return int(rng.integers(120, 720))
        return int(rng.integers(720, 4320))

    # Other / Unknown
    if draw < 0.05:
        return int(rng.integers(60, 240))
    if draw < 0.30:
        return int(rng.integers(240, 1440))
    return int(rng.integers(1440, 5760))

# -----------------------------------------------------------------------------
# Account and rep selection helpers
# -----------------------------------------------------------------------------


def prep_accounts(accounts: pd.DataFrame) -> pd.DataFrame:
    """Prepare account data for lead generation."""
    accounts = accounts.copy()
    accounts["account_domain"] = accounts["account_domain"].map(clean_domain)
    return accounts


def sample_account(
    accounts: pd.DataFrame,
    region: str,
    account_source: str | None,
    rng: np.random.Generator,
    require_domain: bool = True,
) -> pd.Series | None:
    """Sample an account row matching the desired region/source when possible."""
    candidates = accounts[accounts["region"] == region].copy()

    if account_source is not None:
        candidates = candidates[candidates["account_created_source"] == account_source]

    if require_domain:
        candidates = candidates[candidates["account_domain"].notna()]

    if candidates.empty:
        candidates = accounts[accounts["region"] == region].copy()
        if require_domain:
            candidates = candidates[candidates["account_domain"].notna()]

    if candidates.empty:
        return None

    idx = rng.choice(candidates.index.to_numpy())
    return candidates.loc[idx]


def seller_candidates(
    reps: pd.DataFrame,
    territory_id: str,
    segment: str,
    prefer_sdr: bool,
) -> pd.DataFrame:
    """Return sales rep candidates for a lead assignment."""
    candidates = reps[
        (reps["territory_id"] == territory_id)
        & (reps["active_flag"] == 1)
        & (reps["role"].isin(SELLER_ROLES))
    ].copy()

    if candidates.empty:
        return candidates

    if prefer_sdr:
        sdrs = candidates[candidates["role"] == "Sales Development Representative"]
        if not sdrs.empty:
            return sdrs

    if territory_id not in US_SEGMENT_TERRITORIES and segment == "Enterprise":
        eaes = candidates[candidates["role"] == "Enterprise Account Executive"]
        if not eaes.empty:
            return eaes

    aes = candidates[candidates["role"] == "Account Executive"]
    if not aes.empty:
        return aes

    return candidates


def choose_assigned_rep(
    reps: pd.DataFrame,
    territory_id: str | pd.NA,
    segment: str,
    source: str,
    account_owner_id: str | pd.NA,
    account_match_status: str,
    rng: np.random.Generator,
) -> tuple[str | pd.NA, float | pd.NA]:
    """Choose a lead owner and return rep_id plus capacity score."""
    if pd.isna(territory_id):
        return pd.NA, pd.NA

    # Existing-account demo/partner leads often route to account owner / seller.
    direct_to_seller = (
        source in {"Demo Request", "Partner Referral"}
        or account_match_status == "existing_account_match" and rng.random() < 0.35
    )
    prefer_sdr = not direct_to_seller

    if pd.notna(account_owner_id) and direct_to_seller:
        owner = reps.loc[reps["rep_id"] == str(account_owner_id)]
        if not owner.empty and int(owner.iloc[0]["active_flag"]) == 1:
            return str(account_owner_id), float(owner.iloc[0]["capacity_score"])

    candidates = seller_candidates(reps, str(territory_id), segment, prefer_sdr)
    if candidates.empty:
        return pd.NA, pd.NA

    chosen_idx = rng.choice(candidates.index.to_numpy())
    chosen = candidates.loc[chosen_idx]
    return str(chosen["rep_id"]), float(chosen["capacity_score"])


# -----------------------------------------------------------------------------
# Main build
# -----------------------------------------------------------------------------


def build_leads(seed: int = SEED) -> pd.DataFrame:
    """Build the full synthetic lead fact table."""
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    accounts_raw, _ = load_first_available(ACCOUNT_INPUT_CANDIDATES, "accounts")
    reps, _ = load_first_available(SALES_REP_INPUT_CANDIDATES, "sales reps")
    accounts = prep_accounts(accounts_raw)

    lead_ids = [f"LEAD_{i:06d}" for i in range(1, N_LEADS + 1)]
    lead_sources = make_exact_list(LEAD_SOURCE_COUNTS, rng)
    target_regions = make_exact_list(REGION_COUNTS, rng)
    account_match_statuses = make_exact_list(ACCOUNT_MATCH_COUNTS, rng)
    created_dates = random_dates("2024-01-01", "2025-06-30", N_LEADS, rng)

    created_account_pool = (
        accounts.loc[
            accounts["account_created_source"] == "created_from_converted_lead",
            "account_id",
        ]
        .dropna()
        .drop_duplicates()
        .tolist()
    )
    rng.shuffle(created_account_pool)

    records: list[dict[str, Any]] = []
    used_emails: list[str] = []

    for i in range(N_LEADS):
        lead_id = lead_ids[i]
        created_at = created_dates[i]
        source = lead_sources[i]
        target_region = target_regions[i]
        account_match_status = account_match_statuses[i]
        form_completeness = choose_source_adjusted_form_completeness(source, rng)
        email_type = choose_email_type(account_match_status, source, rng)

        account_row = None
        possible_account_id: str | pd.NA = pd.NA
        matched_account_id: str | pd.NA = pd.NA
        account_owner_id: str | pd.NA = pd.NA

        if account_match_status == "existing_account_match":
            account_row = sample_account(accounts, target_region, "seed_existing", rng, require_domain=True)
            if account_row is not None:
                matched_account_id = str(account_row["account_id"])
                possible_account_id = matched_account_id
                account_owner_id = account_row.get("owner_rep_id", pd.NA)

        elif account_match_status == "partial_fuzzy_match":
            account_row = sample_account(accounts, target_region, "seed_existing", rng, require_domain=False)
            if account_row is not None:
                possible_account_id = str(account_row["account_id"])
                account_owner_id = account_row.get("owner_rep_id", pd.NA)

        elif account_match_status == "duplicate_existing_lead_contact":
            account_row = sample_account(accounts, target_region, "seed_existing", rng, require_domain=True)
            if account_row is not None:
                possible_account_id = str(account_row["account_id"])
                matched_account_id = str(account_row["account_id"])
                account_owner_id = account_row.get("owner_rep_id", pd.NA)

        elif account_match_status == "new_account_candidate":
            # Use created-from-lead accounts as templates, but only assign created_account_id after conversion.
            account_row = sample_account(accounts, target_region, "created_from_converted_lead", rng, require_domain=True)

        if account_row is not None and pd.notna(account_row.get("country")):
            country = str(account_row["country"])
            region = str(account_row["region"])
            subregion = str(account_row["subregion"])
            industry = str(account_row["industry"])
            segment = choose_segment(account_row, source, rng)
            account_domain = clean_domain(account_row.get("account_domain"))
            account_name = str(account_row.get("account_name")) if pd.notna(account_row.get("account_name")) else None
            account_fit_score = int(account_row.get("account_fit_score", 50)) if pd.notna(account_row.get("account_fit_score", 50)) else 50
        else:
            region = target_region
            country = weighted_choice(COUNTRY_BY_REGION[region], rng)
            subregion = assign_subregion(country)
            industry = weighted_choice({
                "Technology": 0.22,
                "Financial Services": 0.12,
                "Healthcare": 0.10,
                "Manufacturing": 0.10,
                "Retail / Ecommerce": 0.09,
                "Professional Services": 0.09,
                "Education": 0.07,
                "Media / Entertainment": 0.06,
                "Public Sector / Nonprofit": 0.05,
                "Other / Unknown": 0.10,
            }, rng)
            segment = choose_segment(None, source, rng)
            account_domain = None
            account_name = None
            account_fit_score = 50

        territory_id = assign_territory(region, subregion, segment if segment != "SMB" else "Commercial")

        full_name = fake.name()
        first_last = re.sub(r"[^a-zA-Z. ]", "", full_name).lower().replace(" ", ".")
        first_last = re.sub(r"\.+", ".", first_last).strip(".")

        if email_type == "business_known_domain" and account_domain is not None:
            email_domain = account_domain
        elif email_type == "business_known_domain" and account_domain is None:
            email_domain = f"{fake.domain_word()}.com"
        elif email_type == "business_unknown_domain":
            email_domain = f"{fake.domain_word()}{int(rng.integers(10, 999))}.com"
        elif email_type == "personal_email":
            email_domain = str(rng.choice(PERSONAL_EMAIL_DOMAINS))
        elif email_type == "education_noncommercial":
            email_domain = str(rng.choice(EDU_EMAIL_DOMAINS))
        elif email_type == "invalid_fake_email":
            email_domain = "invalid"
        elif email_type == "duplicate_email" and used_emails:
            email = str(rng.choice(used_emails))
            email_domain = email.split("@")[-1] if "@" in email else "invalid"
        else:
            email_domain = str(rng.choice(DISPOSABLE_DOMAINS))

        if email_type == "invalid_fake_email":
            email = str(rng.choice(INVALID_EMAIL_PATTERNS))
        elif email_type != "duplicate_email" or not used_emails:
            email = f"{first_last}@{email_domain}"

        used_emails.append(email)

        # Form-field flags.
        full_name_provided = form_completeness in {"email_name", "email_name_company_title", "full_profile"}
        company_name_provided = form_completeness in {"email_company", "email_name_company_title", "full_profile"}
        job_title_provided = form_completeness in {"email_name_company_title", "full_profile"}
        country_provided = form_completeness == "full_profile"

        job_function = choose_job_function(source, rng)
        seniority = choose_seniority(job_function, source, rng)

        inferred_company: str | pd.NA = pd.NA
        inferred_country: str | pd.NA = pd.NA
        inferred_region: str | pd.NA = pd.NA

        if company_name_provided and account_name is not None:
            inferred_company = account_name
        elif email_type in {"business_known_domain", "business_unknown_domain"}:
            inferred_company = domain_to_company(email_domain)

        if country_provided:
            inferred_country = country
            inferred_region = region
        elif email_type == "business_known_domain" and account_domain is not None:
            inferred_country = country
            inferred_region = region
        elif email_type == "business_unknown_domain" and rng.random() < 0.55:
            inferred_country = country
            inferred_region = region

        # Enrichment status and confidence.
        if email_type == "invalid_fake_email":
            enrichment_status = "failed_invalid_fake_email"
            enrichment_confidence = rng.uniform(0.0, 0.15)
        elif email_type in {"personal_email", "education_noncommercial"} and not company_name_provided:
            enrichment_status = "failed_personal_email"
            enrichment_confidence = rng.uniform(0.10, 0.35)
        elif account_match_status == "duplicate_existing_lead_contact" or email_type == "duplicate_email":
            enrichment_status = "duplicate_suppressed"
            enrichment_confidence = rng.uniform(0.70, 0.95)
        elif form_completeness == "full_profile" and email_type in {"business_known_domain", "business_unknown_domain"}:
            enrichment_status = "complete"
            enrichment_confidence = rng.uniform(0.86, 0.99)
        elif email_type == "business_known_domain" and account_match_status == "existing_account_match":
            enrichment_status = "domain_inferred"
            enrichment_confidence = rng.uniform(0.78, 0.95)
        elif pd.notna(inferred_country) and pd.isna(inferred_company):
            enrichment_status = "country_inferred_only"
            enrichment_confidence = rng.uniform(0.45, 0.70)
        elif pd.notna(inferred_company) and pd.isna(inferred_country):
            enrichment_status = "company_inferred_only"
            enrichment_confidence = rng.uniform(0.45, 0.72)
        elif email_type in {"business_known_domain", "business_unknown_domain"}:
            enrichment_status = "partial_low_confidence"
            enrichment_confidence = rng.uniform(0.35, 0.65)
        else:
            enrichment_status = "partial_low_confidence"
            enrichment_confidence = rng.uniform(0.20, 0.50)

        missing_required_fields_count = sum([
            not full_name_provided,
            not company_name_provided and pd.isna(inferred_company),
            not job_title_provided,
            not country_provided and pd.isna(inferred_country),
        ])

        # Lead score.
        score = 30
        source_score = {
            "Demo Request": 28,
            "Partner Referral": 22,
            "Paid Search": 15,
            "Free Trial / Free Sample": 12,
            "Webinar": 8,
            "Event Scan": 6,
            "Content Download": 3,
            "Other / Unknown": -4,
        }
        score += source_score[source]

        if segment == "Enterprise":
            score += 12
        elif segment == "Mid-Market":
            score += 8
        elif segment == "Commercial":
            score += 4
        else:
            score -= 5

        if email_type == "business_known_domain":
            score += 12
        elif email_type == "business_unknown_domain":
            score += 6
        elif email_type in {"personal_email", "education_noncommercial"}:
            score -= 10
        elif email_type in {"invalid_fake_email", "disposable_suspicious_domain"}:
            score -= 20
        elif email_type == "duplicate_email":
            score -= 15

        if account_match_status == "existing_account_match":
            score += 10
        elif account_match_status == "new_account_candidate":
            score += 5
        elif account_match_status in {"personal_invalid_no_match", "duplicate_existing_lead_contact"}:
            score -= 15

        if seniority in {"Executive / C-level", "VP / Head of", "Director"}:
            score += 8
        elif seniority in {"Student / Personal Use", "Unknown"}:
            score -= 8

        if job_function in {"IT / Engineering", "Security / Compliance", "Operations", "Executive / Founder"}:
            score += 5
        elif job_function in {"Student / Researcher", "Unknown"}:
            score -= 6

        score += int((account_fit_score - 50) * 0.25)
        score += rng.normal(0, 9)
        lead_score = int(np.clip(round(score), 0, 100))
        mql_flag = int(lead_score >= 50 and enrichment_status not in {"failed_invalid_fake_email", "duplicate_suppressed"})

        # Routing status.
        success_prob = 0.82
        if enrichment_status in {"complete", "domain_inferred"}:
            success_prob += 0.18
        elif enrichment_status in {"country_inferred_only", "company_inferred_only"}:
            success_prob += 0.06
        elif enrichment_status == "partial_low_confidence":
            success_prob -= 0.12
        elif enrichment_status.startswith("failed"):
            success_prob -= 0.32
        elif enrichment_status == "duplicate_suppressed":
            success_prob -= 0.70

        if account_match_status == "existing_account_match":
            success_prob += 0.08
        elif account_match_status == "partial_fuzzy_match":
            success_prob -= 0.04
        elif account_match_status == "personal_invalid_no_match":
            success_prob -= 0.16
        elif account_match_status == "duplicate_existing_lead_contact":
            success_prob -= 0.20

        version = routing_model_version(created_at)
        if version == "v1_baseline":
            success_prob -= 0.14
        elif version == "v2_domain_inference":
            success_prob += 0.03
        elif version == "v3_logic_fix":
            success_prob += 0.14

        success_prob = float(np.clip(success_prob, 0.02, 0.98))
        routing_roll = rng.random()

        if enrichment_status == "duplicate_suppressed" or email_type == "duplicate_email":
            routing_status = "suppressed_duplicate_invalid"
        elif routing_roll < success_prob:
            if enrichment_status in {"domain_inferred", "country_inferred_only", "company_inferred_only", "partial_low_confidence"}:
                routing_status = "routed_after_enrichment"
            else:
                routing_status = "routed_successfully"
        else:
            failure_draw = rng.random()
            if failure_draw < 0.48:
                routing_status = "manual_review"
            elif failure_draw < 0.72:
                routing_status = "fallback_queue"
            else:
                routing_status = "failed_routing"

        routing_failure_reason: str | pd.NA = pd.NA
        if routing_status in {"manual_review", "fallback_queue", "failed_routing", "suppressed_duplicate_invalid"}:
            if routing_status == "suppressed_duplicate_invalid":
                routing_failure_reason = "duplicate_or_invalid_lead"
            elif email_type == "invalid_fake_email":
                routing_failure_reason = "invalid_fake_email"
            elif email_type in {"personal_email", "education_noncommercial"} and pd.isna(inferred_company):
                routing_failure_reason = "personal_email_no_company_match"
            elif pd.isna(inferred_country):
                routing_failure_reason = "missing_country"
            elif pd.isna(inferred_company):
                routing_failure_reason = "missing_company"
            elif account_match_status == "partial_fuzzy_match":
                routing_failure_reason = "conflicting_account_match"
            elif rng.random() < 0.15:
                routing_failure_reason = "territory_rule_gap"
            else:
                routing_failure_reason = "manual_review_required"

        assignment_method: str | pd.NA = pd.NA
        if routing_status == "routed_successfully":
            assignment_method = "direct_rule"
        elif routing_status == "routed_after_enrichment":
            assignment_method = "domain_country_inference"
        elif routing_status == "manual_review":
            assignment_method = "manual_review"
        elif routing_status == "fallback_queue":
            assignment_method = "fallback_queue"

        assigned_rep_id: str | pd.NA = pd.NA
        assigned_rep_capacity: float | pd.NA = pd.NA
        assigned_territory_id: str | pd.NA = pd.NA
        minutes_to_assignment: float | pd.NA = pd.NA

        if routing_status in {"routed_successfully", "routed_after_enrichment", "manual_review", "fallback_queue"}:
            assigned_territory_id = territory_id
            assigned_rep_id, assigned_rep_capacity = choose_assigned_rep(
                reps=reps,
                territory_id=territory_id,
                segment=segment,
                source=source,
                account_owner_id=account_owner_id,
                account_match_status=account_match_status,
                rng=rng,
            )

            if routing_status == "routed_successfully":
                minutes_to_assignment = float(rng.integers(1, 6))
            elif routing_status == "routed_after_enrichment":
                minutes_to_assignment = float(rng.integers(1, 16))
            elif routing_status == "manual_review":
                minutes_to_assignment = float(rng.integers(60, 721))
            else:
                minutes_to_assignment = float(rng.integers(240, 1441))

        # First-touch timing.
        first_touch_completed = 0
        minutes_to_first_touch: float | pd.NA = pd.NA
        first_touch_at: pd.Timestamp | pd.NA = pd.NA

        if pd.notna(assigned_rep_id) and pd.notna(minutes_to_assignment):
            touch_prob = 0.88
            if source in {"Demo Request", "Partner Referral"}:
                touch_prob += 0.08
            elif source in {"Content Download", "Other / Unknown"}:
                touch_prob -= 0.08

            if mql_flag == 0:
                touch_prob -= 0.18
            if pd.notna(assigned_rep_capacity) and assigned_rep_capacity > 90:
                touch_prob -= 0.10
            if routing_status in {"manual_review", "fallback_queue"}:
                touch_prob -= 0.15

            touch_prob = float(np.clip(touch_prob, 0.15, 0.98))
            if rng.random() < touch_prob:
                first_touch_completed = 1
                capacity_delay = 0
                if pd.notna(assigned_rep_capacity):
                    capacity_delay = max(0, (float(assigned_rep_capacity) - 80) * 0.8)

                source_delay = choose_source_response_delay(source, rng)

                total_minutes = minutes_to_assignment + source_delay + capacity_delay + rng.normal(0, 20)
                minutes_to_first_touch = float(max(1, round(total_minutes)))
                first_touch_at = created_at + pd.Timedelta(minutes=int(minutes_to_first_touch))

        speed_to_lead_bucket = speed_bucket(minutes_to_first_touch)

        records.append({
            "lead_id": lead_id,
            "created_at": created_at,
            "created_month": created_at.strftime("%Y-%m"),
            "created_quarter": f"{created_at.year}-Q{created_at.quarter}",
            "routing_model_version": version,
            "lead_source": source,
            "region": region,
            "subregion": subregion,
            "country": country,
            "segment": segment,
            "industry": industry,
            "email": email,
            "email_domain": email_domain,
            "email_type": email_type,
            "form_completeness": form_completeness,
            "full_name_provided": int(full_name_provided),
            "company_name_provided": int(company_name_provided),
            "job_title_provided": int(job_title_provided),
            "country_provided": int(country_provided),
            "inferred_company": inferred_company,
            "inferred_country": inferred_country,
            "inferred_region": inferred_region,
            "account_match_status": account_match_status,
            "matched_account_id": matched_account_id,
            "possible_account_id": possible_account_id,
            "created_account_id": pd.NA,
            "created_contact_id": pd.NA,
            "job_function": job_function,
            "seniority": seniority,
            "lead_score": lead_score,
            "lead_score_band": lead_score_band(lead_score),
            "mql_flag": mql_flag,
            "enrichment_status": enrichment_status,
            "enrichment_confidence_score": round(float(enrichment_confidence), 3),
            "missing_required_fields_count": int(missing_required_fields_count),
            "routing_status": routing_status,
            "routing_failure_reason": routing_failure_reason,
            "assignment_method": assignment_method,
            "assigned_rep_id": assigned_rep_id,
            "assigned_territory_id": assigned_territory_id,
            "minutes_to_assignment": minutes_to_assignment,
            "first_touch_at": first_touch_at,
            "minutes_to_first_touch": minutes_to_first_touch,
            "speed_to_lead_bucket": speed_to_lead_bucket,
            "first_touch_completed": first_touch_completed,
            "converted_to_contact": 0,
            "converted_to_account": 0,
            "converted_to_opportunity": 0,
            "created_opportunity_id": pd.NA,
            "conversion_outcome": "not_converted",
            "non_conversion_reason": pd.NA,
            "data_quality_score": pd.NA,
            "data_quality_tier": pd.NA,
        })

    leads = pd.DataFrame(records)

    # Conversion propensity and deterministic target counts.
    propensity = np.zeros(len(leads), dtype=float)
    propensity += leads["lead_score"] / 100 * 0.35
    propensity += leads["mql_flag"] * 0.15
    propensity += leads["first_touch_completed"] * 0.15
    propensity += leads["speed_to_lead_bucket"].map({
        "0-15 minutes": 0.18,
        "16-60 minutes": 0.14,
        "1-4 hours": 0.08,
        "Same day": 0.02,
        "1-3 days": -0.06,
        "4+ days": -0.12,
        "No touch": -0.20,
    }).astype(float).to_numpy()
    propensity += leads["lead_source"].map({
        "Demo Request": 0.18,
        "Partner Referral": 0.14,
        "Paid Search": 0.06,
        "Free Trial / Free Sample": 0.04,
        "Webinar": 0.02,
        "Event Scan": 0.00,
        "Content Download": -0.05,
        "Other / Unknown": -0.08,
    }).astype(float).to_numpy()
    propensity += leads["account_match_status"].map({
        "existing_account_match": 0.08,
        "new_account_candidate": 0.04,
        "partial_fuzzy_match": -0.04,
        "no_account_match": -0.08,
        "personal_invalid_no_match": -0.18,
        "duplicate_existing_lead_contact": -0.20,
    }).astype(float).to_numpy()
    propensity += rng.normal(0, 0.06, len(leads))

    eligible_contact = (
        (leads["mql_flag"] == 1)
        & (leads["first_touch_completed"] == 1)
        & (~leads["enrichment_status"].isin(["failed_invalid_fake_email", "duplicate_suppressed"]))
        & (~leads["routing_status"].isin(["failed_routing", "suppressed_duplicate_invalid"]))
    )

    contact_target = 2800
    eligible_indices = leads.index[eligible_contact].to_numpy()
    ranked_contact_indices = eligible_indices[np.argsort(propensity[eligible_indices])[::-1]]
    converted_contact_indices = ranked_contact_indices[:contact_target]
    leads.loc[converted_contact_indices, "converted_to_contact"] = 1

    # Create contacts.
    contact_ids = [f"CON_{i:06d}" for i in range(1, len(converted_contact_indices) + 1)]
    leads.loc[converted_contact_indices, "created_contact_id"] = contact_ids

    # Account conversion: existing matched accounts count as converted to account; net-new creates account.
    converted_mask = leads["converted_to_contact"] == 1
    matched_account_mask = converted_mask & leads["matched_account_id"].notna()
    leads.loc[matched_account_mask, "converted_to_account"] = 1

    new_account_candidates = leads.index[
        converted_mask
        & (leads["account_match_status"] == "new_account_candidate")
    ].to_numpy().copy()
    rng.shuffle(new_account_candidates)
    created_account_count = min(len(created_account_pool), len(new_account_candidates))
    created_account_indices = new_account_candidates[:created_account_count]
    leads.loc[created_account_indices, "created_account_id"] = created_account_pool[:created_account_count]
    leads.loc[created_account_indices, "converted_to_account"] = 1

    # Opportunity conversion among converted leads with account context.
    account_context_mask = converted_mask & (
        leads["matched_account_id"].notna() | leads["created_account_id"].notna()
    )
    opp_eligible_indices = leads.index[account_context_mask].to_numpy()

    opp_propensity = propensity.copy()
    opp_propensity += leads["lead_source"].map({
        "Demo Request": 0.16,
        "Partner Referral": 0.10,
        "Paid Search": 0.06,
        "Free Trial / Free Sample": 0.04,
        "Webinar": 0.01,
        "Event Scan": -0.02,
        "Content Download": -0.06,
        "Other / Unknown": -0.10,
    }).astype(float).to_numpy()
    opp_propensity += rng.normal(0, 0.05, len(leads))

    opp_target = 1300
    ranked_opp_indices = opp_eligible_indices[np.argsort(opp_propensity[opp_eligible_indices])[::-1]]
    converted_opp_indices = ranked_opp_indices[:min(opp_target, len(ranked_opp_indices))]
    leads.loc[converted_opp_indices, "converted_to_opportunity"] = 1
    leads.loc[converted_opp_indices, "created_opportunity_id"] = [
        f"OPP_{i:06d}" for i in range(1, len(converted_opp_indices) + 1)
    ]

    # Conversion outcome and non-conversion reason.
    leads.loc[leads["converted_to_contact"] == 1, "conversion_outcome"] = "converted_contact_only"
    leads.loc[
        (leads["converted_to_contact"] == 1) & (leads["converted_to_account"] == 1),
        "conversion_outcome",
    ] = "converted_contact_account"
    leads.loc[
        leads["converted_to_opportunity"] == 1,
        "conversion_outcome",
    ] = "converted_contact_account_opportunity"

    non_converted = leads["converted_to_contact"] == 0
    reason_weights = {
        "no_response": 0.28,
        "bad_contact_data": 0.16,
        "unqualified_low_fit": 0.16,
        "routed_late": 0.12,
        "duplicate_or_suppressed": 0.08,
        "student_or_personal_use": 0.08,
        "unsupported_or_unknown_region": 0.04,
        "low_intent_source": 0.08,
    }

    reasons = []
    for _, row in leads.loc[non_converted].iterrows():
        if row["routing_status"] == "suppressed_duplicate_invalid" or row["enrichment_status"] == "duplicate_suppressed":
            reasons.append("duplicate_or_suppressed")
        elif row["email_type"] in {"invalid_fake_email", "disposable_suspicious_domain"}:
            reasons.append("bad_contact_data")
        elif row["seniority"] == "Student / Personal Use" or row["job_function"] == "Student / Researcher":
            reasons.append("student_or_personal_use")
        elif row["speed_to_lead_bucket"] in {"1-3 days", "4+ days", "No touch"}:
            reasons.append("routed_late")
        elif row["lead_score"] < 50:
            reasons.append("unqualified_low_fit")
        else:
            reasons.append(weighted_choice(reason_weights, rng))

    leads.loc[non_converted, "non_conversion_reason"] = reasons

    # Lead data quality score.
    leads["data_quality_score"] = leads.apply(calculate_lead_data_quality_score, axis=1)
    leads["data_quality_tier"] = leads["data_quality_score"].apply(data_quality_tier)

    # Clean date/datetime fields for CSV output.
    leads["created_at"] = pd.to_datetime(leads["created_at"]).dt.date
    leads["first_touch_at"] = pd.to_datetime(leads["first_touch_at"], errors="coerce")

    # Nullable numeric fields.
    leads["minutes_to_assignment"] = pd.to_numeric(leads["minutes_to_assignment"], errors="coerce").round(0).astype("Int64")
    leads["minutes_to_first_touch"] = pd.to_numeric(leads["minutes_to_first_touch"], errors="coerce").round(0).astype("Int64")
    leads["data_quality_score"] = leads["data_quality_score"].astype(int)

    return leads[EXPECTED_COLUMNS]


# -----------------------------------------------------------------------------
# Data quality scoring
# -----------------------------------------------------------------------------


def calculate_lead_data_quality_score(row: pd.Series) -> int:
    """Score lead record quality from 0 to 100."""
    score = 0

    # Email quality: max 25.
    if row["email_type"] == "business_known_domain":
        score += 25
    elif row["email_type"] == "business_unknown_domain":
        score += 18
    elif row["email_type"] in {"personal_email", "education_noncommercial"}:
        score += 10
    elif row["email_type"] == "duplicate_email":
        score += 6
    else:
        score += 0

    # Form completeness: max 20.
    score += {
        "email_only": 4,
        "email_name": 8,
        "email_company": 11,
        "email_name_company_title": 16,
        "full_profile": 20,
    }[row["form_completeness"]]

    # Account/enrichment quality: max 25.
    if row["account_match_status"] == "existing_account_match":
        score += 15
    elif row["account_match_status"] == "new_account_candidate":
        score += 10
    elif row["account_match_status"] == "partial_fuzzy_match":
        score += 7
    elif row["account_match_status"] == "no_account_match":
        score += 3

    if row["enrichment_status"] in {"complete", "domain_inferred"}:
        score += 10
    elif row["enrichment_status"] in {"country_inferred_only", "company_inferred_only"}:
        score += 6
    elif row["enrichment_status"] == "partial_low_confidence":
        score += 3

    # Routeability: max 20.
    if row["routing_status"] == "routed_successfully":
        score += 20
    elif row["routing_status"] == "routed_after_enrichment":
        score += 17
    elif row["routing_status"] == "manual_review":
        score += 10
    elif row["routing_status"] == "fallback_queue":
        score += 6

    # Territory/rep assignment: max 10.
    if pd.notna(row["assigned_territory_id"]):
        score += 5
    if pd.notna(row["assigned_rep_id"]):
        score += 5

    return int(np.clip(score, 0, 100))


def data_quality_tier(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 55:
        return "partial"
    return "poor"


# -----------------------------------------------------------------------------
# Validation and output
# -----------------------------------------------------------------------------


def validate_leads(leads: pd.DataFrame) -> None:
    """Validate fact_leads and print useful checks."""
    errors: list[str] = []

    if list(leads.columns) != EXPECTED_COLUMNS:
        errors.append("Unexpected column order or missing/extra columns.")

    if len(leads) != N_LEADS:
        errors.append(f"Expected {N_LEADS} leads, found {len(leads)}.")

    if leads["lead_id"].duplicated().any():
        errors.append("Duplicate lead_id values found.")

    for required_column in ["lead_id", "created_at", "lead_source", "email", "email_type"]:
        if leads[required_column].isna().any():
            errors.append(f"Null values found in required column: {required_column}")

    accounts, _ = load_first_available(ACCOUNT_INPUT_CANDIDATES, "accounts")
    reps, _ = load_first_available(SALES_REP_INPUT_CANDIDATES, "sales reps")

    account_ids = set(accounts["account_id"].dropna().astype(str))
    rep_ids = set(reps["rep_id"].dropna().astype(str))

    for column in ["matched_account_id", "possible_account_id", "created_account_id"]:
        values = set(leads[column].dropna().astype(str))
        missing = sorted(values - account_ids)
        if missing:
            errors.append(f"{column} has IDs missing from dim_accounts: {missing[:10]}")

    assigned_reps = set(leads["assigned_rep_id"].dropna().astype(str))
    missing_reps = sorted(assigned_reps - rep_ids)
    if missing_reps:
        errors.append(f"assigned_rep_id has IDs missing from dim_sales_reps: {missing_reps[:10]}")

    if leads["converted_to_contact"].sum() != 2800:
        errors.append("Expected exactly 2,800 converted contacts.")

    if leads["converted_to_opportunity"].sum() != 1300:
        errors.append("Expected exactly 1,300 converted opportunities.")

    if errors:
        error_text = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"fact_leads validation failed:\n{error_text}")

    print("Validation passed: fact_leads is valid.")


def print_summary(leads: pd.DataFrame) -> None:
    """Print human-readable summary checks."""
    print("\nTotal leads:", len(leads))

    print("\nLead source counts:")
    print(leads["lead_source"].value_counts().to_string())

    print("\nRegion counts:")
    print(leads["region"].value_counts(dropna=False).sort_index().to_string())

    print("\nAccount match status counts:")
    print(leads["account_match_status"].value_counts(dropna=False).to_string())

    print("\nEmail type counts:")
    print(leads["email_type"].value_counts(dropna=False).to_string())

    print("\nForm completeness counts:")
    print(leads["form_completeness"].value_counts(dropna=False).to_string())

    print("\nEnrichment status counts:")
    print(leads["enrichment_status"].value_counts(dropna=False).to_string())

    print("\nRouting status counts:")
    print(leads["routing_status"].value_counts(dropna=False).to_string())

    print("\nRouting model version by routing status:")
    print(pd.crosstab(leads["routing_model_version"], leads["routing_status"]).to_string())

    print("\nSpeed-to-lead bucket counts:")
    print(leads["speed_to_lead_bucket"].value_counts(dropna=False).to_string())

    print("\nConversion outcome counts:")
    print(leads["conversion_outcome"].value_counts(dropna=False).to_string())

    print("\nFunnel counts:")
    funnel = pd.Series({
        "total_leads": len(leads),
        "mqls": int(leads["mql_flag"].sum()),
        "assigned": int(leads["assigned_rep_id"].notna().sum()),
        "first_touch_completed": int(leads["first_touch_completed"].sum()),
        "converted_to_contact": int(leads["converted_to_contact"].sum()),
        "converted_to_account": int(leads["converted_to_account"].sum()),
        "converted_to_opportunity": int(leads["converted_to_opportunity"].sum()),
    })
    print(funnel.to_string())

    print("\nMQL-to-opportunity conversion rate by speed bucket:")
    speed_summary = leads.groupby("speed_to_lead_bucket", dropna=False).agg(
        leads=("lead_id", "count"),
        mqls=("mql_flag", "sum"),
        opportunities=("converted_to_opportunity", "sum"),
    )
    speed_summary["opp_rate"] = (speed_summary["opportunities"] / speed_summary["leads"]).round(3)
    print(speed_summary.to_string())

    print("\nRouting success rate by email type:")
    route_success = leads.assign(
        routed_success=leads["routing_status"].isin(["routed_successfully", "routed_after_enrichment"]).astype(int)
    ).groupby("email_type").agg(
        leads=("lead_id", "count"),
        routed_success=("routed_success", "mean"),
    )
    route_success["routed_success"] = route_success["routed_success"].round(3)
    print(route_success.to_string())

    print("\nData quality tier counts:")
    print(leads["data_quality_tier"].value_counts(dropna=False).to_string())

    print("\nPreview:")
    print(leads.head(10).to_string(index=False))


def save_leads(leads: pd.DataFrame) -> Path:
    """Save leads to data/processed."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    leads.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved leads to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    leads_df = build_leads()
    validate_leads(leads_df)
    print_summary(leads_df)
    save_leads(leads_df)
