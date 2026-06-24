"""
Generate a synthetic sales representative dimension table for a GTM / RevOps portfolio project.

This script creates dim_sales_reps.csv using the territory and owner structure from
an existing dim_accounts.csv when available. It is designed to match the current
account-generation logic, including AMER segment territories, international
enterprise coverage, SDR coverage, Regional VPs by territory, and Area VPs by region.

Output:
    data/processed/dim_sales_reps.csv

Run from the project root:
    python src/generate_sales_reps.py
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd
from faker import Faker


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SEED = 42
OUTPUT_FILE = Path("data/processed/dim_sales_reps.csv")

ACCOUNT_INPUT_CANDIDATES = [
    Path("data/processed/dim_accounts.csv"),
    Path("data/raw/dim_accounts.csv"),
    Path("data/raw/accounts.csv"),
    Path("dim_accounts.csv"),
]

EXPECTED_COLUMNS = [
    "rep_id",
    "rep_name",
    "region",
    "territory_id",
    "team",
    "role",
    "active_flag",
    "capacity_score",
]

VALID_REGIONS = {"AMER", "EMEA", "APJ"}

VALID_ROLES = {
    "Account Executive",
    "Enterprise Account Executive",
    "Sales Development Representative",
    "Regional VP",
    "Area VP",
}

# Fallback mirrors the territory/rep structure used by generate_accounts.py.
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

REGION_BY_TERRITORY = {
    "AMER_ENT": "AMER",
    "AMER_MM": "AMER",
    "AMER_COMM": "AMER",
    "LATAM": "AMER",
    "UKI": "EMEA",
    "DACH": "EMEA",
    "FR_BENELUX": "EMEA",
    "NORDICS": "EMEA",
    "SOUTHERN_EUROPE": "EMEA",
    "MEA": "EMEA",
    "INDIA": "APJ",
    "JAPAN_KOREA": "APJ",
    "ANZ": "APJ",
    "SEA": "APJ",
}

TEAM_BY_TERRITORY = {
    "AMER_ENT": "US Enterprise",
    "AMER_MM": "US Mid-Market",
    "AMER_COMM": "US Commercial",
    "LATAM": "LATAM",
    "UKI": "EMEA UKI",
    "DACH": "EMEA DACH",
    "FR_BENELUX": "EMEA France/Benelux",
    "NORDICS": "EMEA Nordics",
    "SOUTHERN_EUROPE": "EMEA Southern Europe",
    "MEA": "EMEA Middle East/Africa",
    "INDIA": "APJ India",
    "JAPAN_KOREA": "APJ Japan/Korea",
    "ANZ": "APJ ANZ",
    "SEA": "APJ Southeast Asia",
}

TERRITORY_ORDER = list(REPS_BY_TERRITORY.keys())
US_SEGMENT_TERRITORIES = {"AMER_ENT", "AMER_MM", "AMER_COMM"}
NON_US_ENTERPRISE_COVERAGE_TERRITORIES = set(TERRITORY_ORDER) - US_SEGMENT_TERRITORIES


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def load_accounts() -> tuple[pd.DataFrame | None, Path | None]:
    """Load dim_accounts.csv if available."""
    for path in ACCOUNT_INPUT_CANDIDATES:
        if path.exists():
            accounts = pd.read_csv(path)
            print(f"Loaded accounts from: {path}")
            return accounts, path

    print("No account CSV found. Using fallback sales territory structure.")
    return None, None


def sort_territories(territories: list[str]) -> list[str]:
    """Sort known territories in business order, then append unknowns alphabetically."""
    known = [territory for territory in TERRITORY_ORDER if territory in territories]
    unknown = sorted([territory for territory in territories if territory not in TERRITORY_ORDER])
    return known + unknown


def load_owner_rep_map(accounts: pd.DataFrame | None) -> dict[str, list[str]]:
    """
    Return a territory -> owner rep list.

    When accounts are available, use non-null account owner assignments, excluding
    INACTIVE_REP because that value represents a data-quality issue rather than a
    real sales rep dimension member.
    """
    if accounts is None:
        return {territory: reps.copy() for territory, reps in REPS_BY_TERRITORY.items()}

    required_cols = {"territory_id", "owner_rep_id"}
    if not required_cols.issubset(accounts.columns):
        missing = required_cols - set(accounts.columns)
        raise ValueError(f"Account file is missing required columns: {sorted(missing)}")

    clean_owner_rows = accounts[
        accounts["territory_id"].notna()
        & accounts["owner_rep_id"].notna()
        & (accounts["owner_rep_id"] != "INACTIVE_REP")
    ].copy()

    owner_map = {}
    territories = sort_territories(clean_owner_rows["territory_id"].dropna().unique().tolist())

    for territory in territories:
        reps = (
            clean_owner_rows.loc[
                clean_owner_rows["territory_id"] == territory,
                "owner_rep_id",
            ]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        owner_map[territory] = reps

    return owner_map


def infer_region(territory_id: str, accounts: pd.DataFrame | None) -> str:
    """Infer region from account data or the territory mapping."""
    if territory_id in REGION_BY_TERRITORY:
        return REGION_BY_TERRITORY[territory_id]

    if accounts is not None and {"territory_id", "region"}.issubset(accounts.columns):
        regions = (
            accounts.loc[accounts["territory_id"] == territory_id, "region"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )
        if len(regions) == 1:
            return str(regions[0])

    raise ValueError(f"Could not infer region for territory_id: {territory_id}")


def team_name(territory_id: str, region: str) -> str:
    """Return readable team name for a territory."""
    if territory_id in TEAM_BY_TERRITORY:
        return TEAM_BY_TERRITORY[territory_id]

    cleaned = re.sub(r"[_-]+", " ", territory_id).title()
    return f"{region} {cleaned}"


def unique_name(fake: Faker, used_names: set[str]) -> str:
    """Generate a unique fake person name."""
    for _ in range(200):
        name = fake.name()
        if name not in used_names:
            used_names.add(name)
            return name

    fallback = f"{fake.name()} {len(used_names) + 1}"
    used_names.add(fallback)
    return fallback


def assign_seller_role(territory_id: str, rep_position: int) -> str:
    """
    Assign seller role based on the requested GTM coverage model.

    US segment territories use Account Executives only because territory determines
    business segment. LATAM, EMEA, and APJ receive Enterprise AE coverage for
    enterprise accounts, while remaining seller reps are AEs for MM/Commercial.
    """
    if territory_id in US_SEGMENT_TERRITORIES:
        return "Account Executive"

    if territory_id in NON_US_ENTERPRISE_COVERAGE_TERRITORIES and rep_position == 1:
        return "Enterprise Account Executive"

    return "Account Executive"


def capacity_score(role: str, rng: np.random.Generator) -> float:
    """
    Generate a synthetic workload pressure score.

    Interpretation:
        0-60    lower current load
        60-80   normal to busy
        80-100  capacity constrained
        100+    overloaded
    """
    role_base = {
        "Account Executive": 76,
        "Enterprise Account Executive": 72,
        "Sales Development Representative": 82,
        "Regional VP": 64,
        "Area VP": 58,
    }

    score = rng.normal(loc=role_base[role], scale=12)

    # Add realistic overloaded pockets among quota-carrying / lead-facing roles.
    if role in {"Account Executive", "Enterprise Account Executive", "Sales Development Representative"}:
        if rng.random() < 0.16:
            score += rng.uniform(12, 25)

    return round(float(np.clip(score, 35, 115)), 1)


# -----------------------------------------------------------------------------
# Build sales reps
# -----------------------------------------------------------------------------


def build_sales_reps(seed: int = SEED) -> pd.DataFrame:
    """Build dim_sales_reps."""
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    accounts, _ = load_accounts()
    owner_map = load_owner_rep_map(accounts)

    records = []
    used_names = set()

    for territory_id in sort_territories(list(owner_map.keys())):
        region = infer_region(territory_id, accounts)
        team = team_name(territory_id, region)
        owner_reps = owner_map[territory_id]

        for position, rep_id in enumerate(owner_reps, start=1):
            role = assign_seller_role(territory_id, position)

            records.append({
                "rep_id": rep_id,
                "rep_name": unique_name(fake, used_names),
                "region": region,
                "territory_id": territory_id,
                "team": team,
                "role": role,
                "active_flag": 1,
                "capacity_score": capacity_score(role, rng),
            })

        # One SDR per territory.
        sdr_role = "Sales Development Representative"
        records.append({
            "rep_id": f"REP_SDR_{territory_id}_01",
            "rep_name": unique_name(fake, used_names),
            "region": region,
            "territory_id": territory_id,
            "team": team,
            "role": sdr_role,
            "active_flag": 1,
            "capacity_score": capacity_score(sdr_role, rng),
        })

        # One Regional VP per territory.
        rvp_role = "Regional VP"
        records.append({
            "rep_id": f"REP_RVP_{territory_id}",
            "rep_name": unique_name(fake, used_names),
            "region": region,
            "territory_id": territory_id,
            "team": team,
            "role": rvp_role,
            "active_flag": 1,
            "capacity_score": capacity_score(rvp_role, rng),
        })

    # Three Area VPs: AMER, EMEA, APJ.
    for region in ["AMER", "EMEA", "APJ"]:
        avp_role = "Area VP"
        records.append({
            "rep_id": f"REP_AVP_{region}",
            "rep_name": unique_name(fake, used_names),
            "region": region,
            "territory_id": f"{region}_ALL",
            "team": f"{region} Area Leadership",
            "role": avp_role,
            "active_flag": 1,
            "capacity_score": capacity_score(avp_role, rng),
        })

    reps = pd.DataFrame(records)
    reps = reps[EXPECTED_COLUMNS].copy()
    return reps


# -----------------------------------------------------------------------------
# Validation and output
# -----------------------------------------------------------------------------


def validate_sales_reps(reps: pd.DataFrame) -> None:
    """Validate dim_sales_reps and print useful checks."""
    errors = []

    if list(reps.columns) != EXPECTED_COLUMNS:
        errors.append(f"Unexpected column order or columns: {list(reps.columns)}")

    if reps["rep_id"].duplicated().any():
        errors.append("Duplicate rep_id values found.")

    null_counts = reps[EXPECTED_COLUMNS].isna().sum()
    null_counts = null_counts[null_counts > 0]
    if not null_counts.empty:
        errors.append(f"Null values found: {null_counts.to_dict()}")

    invalid_regions = sorted(set(reps["region"]) - VALID_REGIONS)
    if invalid_regions:
        errors.append(f"Invalid region values found: {invalid_regions}")

    invalid_roles = sorted(set(reps["role"]) - VALID_ROLES)
    if invalid_roles:
        errors.append(f"Invalid role values found: {invalid_roles}")

    invalid_active_flags = sorted(set(reps["active_flag"]) - {0, 1})
    if invalid_active_flags:
        errors.append(f"Invalid active_flag values found: {invalid_active_flags}")

    if not pd.api.types.is_numeric_dtype(reps["capacity_score"]):
        errors.append("capacity_score must be numeric.")
    elif (reps["capacity_score"].lt(0).any() or reps["capacity_score"].gt(120).any()):
        errors.append("capacity_score values must be between 0 and 120.")

    for territory_id in TERRITORY_ORDER:
        territory_reps = reps[reps["territory_id"] == territory_id]
        if territory_reps.empty:
            continue

        rvp_count = (territory_reps["role"] == "Regional VP").sum()
        sdr_count = (territory_reps["role"] == "Sales Development Representative").sum()

        if rvp_count != 1:
            errors.append(f"{territory_id} must have exactly one Regional VP; found {rvp_count}.")
        if sdr_count != 1:
            errors.append(f"{territory_id} must have exactly one SDR; found {sdr_count}.")

        seller_reps = territory_reps[territory_reps["role"].isin([
            "Account Executive",
            "Enterprise Account Executive",
        ])]

        if seller_reps.empty:
            errors.append(f"{territory_id} has no seller reps.")

        if territory_id in US_SEGMENT_TERRITORIES:
            non_ae_us_sellers = seller_reps[seller_reps["role"] != "Account Executive"]
            if not non_ae_us_sellers.empty:
                errors.append(f"{territory_id} seller reps must all be Account Executives.")

        if territory_id in NON_US_ENTERPRISE_COVERAGE_TERRITORIES:
            eae_count = (seller_reps["role"] == "Enterprise Account Executive").sum()
            if eae_count < 1:
                errors.append(f"{territory_id} must have at least one Enterprise AE.")

    for region in ["AMER", "EMEA", "APJ"]:
        avp_count = ((reps["region"] == region) & (reps["role"] == "Area VP")).sum()
        if avp_count != 1:
            errors.append(f"{region} must have exactly one Area VP; found {avp_count}.")

    # Check coverage of account owner IDs if account data exists.
    accounts, _ = load_accounts()
    if accounts is not None and "owner_rep_id" in accounts.columns:
        account_owner_ids = set(
            accounts["owner_rep_id"]
            .dropna()
            .astype(str)
            .loc[lambda s: s != "INACTIVE_REP"]
            .unique()
        )
        dim_rep_ids = set(reps["rep_id"])
        missing_owner_ids = sorted(account_owner_ids - dim_rep_ids)

        if missing_owner_ids:
            errors.append(
                "Non-null account owner_rep_id values missing from dim_sales_reps: "
                f"{missing_owner_ids[:10]}"
            )

    if errors:
        error_text = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"dim_sales_reps validation failed:\n{error_text}")

    print("Validation passed: dim_sales_reps is valid.")


def print_summary(reps: pd.DataFrame) -> None:
    """Print human-readable summary checks."""
    print("\nTotal sales rep rows:", len(reps))

    print("\nRole counts:")
    print(reps["role"].value_counts().to_string())

    print("\nRegion counts:")
    print(reps["region"].value_counts().sort_index().to_string())

    print("\nSeller role counts by territory:")
    seller_roles = reps[reps["role"].isin(["Account Executive", "Enterprise Account Executive"])]
    print(pd.crosstab(seller_roles["territory_id"], seller_roles["role"]).to_string())

    print("\nLeadership coverage:")
    leadership = reps[reps["role"].isin(["Regional VP", "Area VP"])]
    print(leadership[["rep_id", "rep_name", "region", "territory_id", "team", "role"]].to_string(index=False))

    print("\nTop 10 highest capacity scores:")
    print(reps.sort_values("capacity_score", ascending=False).head(10).to_string(index=False))

    print("\nPreview:")
    print(reps.head(12).to_string(index=False))


def save_sales_reps(reps: pd.DataFrame) -> Path:
    """Save dim_sales_reps to data/processed."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    reps.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved sales reps to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    sales_reps_df = build_sales_reps()
    validate_sales_reps(sales_reps_df)
    print_summary(sales_reps_df)
    save_sales_reps(sales_reps_df)
