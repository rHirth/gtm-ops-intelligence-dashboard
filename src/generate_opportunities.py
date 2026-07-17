"""
Generate synthetic opportunity fact and loss-reason dimension tables for a GTM / RevOps portfolio project.

This script creates:
    data/processed/dim_loss_reasons.csv
    data/processed/fact_opportunities.csv

It uses the existing v0.1 foundation files:
    data/processed/dim_accounts.csv
    data/processed/dim_sales_reps.csv
    data/processed/fact_leads.csv

Business purpose:
    Build the v0.2 opportunity layer so the dashboard can analyze Closed-Lost
    opportunities and trace a subset of losses back to upstream GTM operations
    friction such as routing delay, slow first touch, weak enrichment, stale
    opportunity stage age, missing next steps, low activity, and rep capacity.

Run from the project root:
    python src/generate_opportunities.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SEED = 42

N_OPPORTUNITIES = 1800
N_CONVERTED_MQL_OPPORTUNITIES = 1300
N_SALES_GENERATED_OPPORTUNITIES = 350
N_EXPANSION_OPPORTUNITIES = 150

CLOSED_WON_TARGET = 400
CLOSED_LOST_TARGET = 800
OPEN_TARGET = 600

ACCOUNTS_INPUT = Path("data/processed/dim_accounts.csv")
LEADS_INPUT = Path("data/processed/fact_leads.csv")
SALES_REPS_INPUT = Path("data/processed/dim_sales_reps.csv")

LOSS_REASONS_OUTPUT = Path("data/processed/dim_loss_reasons.csv")
OPPORTUNITIES_OUTPUT = Path("data/processed/fact_opportunities.csv")

SELLER_ROLES = {"Account Executive", "Enterprise Account Executive"}

EXPECTED_LOSS_REASON_COLUMNS = [
    "loss_reason_id",
    "loss_reason",
    "loss_reason_category",
    "controllable_flag",
]

EXPECTED_OPPORTUNITY_COLUMNS = [
    "opportunity_id",
    "account_id",
    "originating_lead_id",
    "owner_rep_id",
    "created_at",
    "close_date",
    "stage",
    "amount",
    "is_closed",
    "is_won",
    "is_closed_lost",
    "opportunity_source",
    "lead_source",
    "region",
    "territory_id",
    "segment",
    "industry",
    "sales_cycle_days",
    "loss_reason_id",
    "loss_reason",
    "loss_reason_category",
    "controllable_loss_flag",
    "days_in_stage",
    "activity_count",
    "days_since_last_activity",
    "next_step_exists",
    "operational_risk_score",
]

STAGE_ORDER = [
    "Qualification",
    "Discovery",
    "Demo",
    "Proposal",
    "Negotiation",
]

STAGE_BENCHMARK_DAYS = {
    "Qualification": 14,
    "Discovery": 21,
    "Demo": 21,
    "Proposal": 30,
    "Negotiation": 30,
    "Closed Won": 0,
    "Closed Lost": 0,
}


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------


def load_required_csv(path: Path, label: str) -> pd.DataFrame:
    """Load a required CSV and raise a clear error if it is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Could not find {label}: {path}")

    df = pd.read_csv(path)
    print(f"Loaded {label} from: {path}")
    return df


def normalize_date(value: Any) -> pd.Timestamp:
    """Convert a value to pandas Timestamp."""
    return pd.to_datetime(value, errors="coerce")


# -----------------------------------------------------------------------------
# Dimension table
# -----------------------------------------------------------------------------


def build_loss_reasons() -> pd.DataFrame:
    """Build dim_loss_reasons using the categories already defined for Closed-Lost analysis."""
    records = [
        {
            "loss_reason_id": "LR_NO_BUDGET",
            "loss_reason": "No budget",
            "loss_reason_category": "Commercial",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_NO_DECISION",
            "loss_reason": "No decision",
            "loss_reason_category": "Timing",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_COMPETITOR_SELECTED",
            "loss_reason": "Competitor selected",
            "loss_reason_category": "Competitive",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_POOR_FIT",
            "loss_reason": "Poor fit",
            "loss_reason_category": "Qualification",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_TIMING",
            "loss_reason": "Timing",
            "loss_reason_category": "Timing",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_UNRESPONSIVE",
            "loss_reason": "Unresponsive",
            "loss_reason_category": "Operational",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_PRICE",
            "loss_reason": "Price",
            "loss_reason_category": "Commercial",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_MISSING_DECISION_MAKER",
            "loss_reason": "Missing decision maker",
            "loss_reason_category": "Operational",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_DUPLICATE_BAD_DATA",
            "loss_reason": "Duplicate / bad data",
            "loss_reason_category": "Data Quality",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_SLOW_FOLLOW_UP",
            "loss_reason": "Slow follow-up",
            "loss_reason_category": "Operational",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_TERRITORY_CONFUSION",
            "loss_reason": "Territory ownership confusion",
            "loss_reason_category": "Operational",
            "controllable_flag": 1,
        },
        {
            "loss_reason_id": "LR_TECHNICAL_MISMATCH",
            "loss_reason": "Technical requirements mismatch",
            "loss_reason_category": "Product Fit",
            "controllable_flag": 0,
        },
        {
            "loss_reason_id": "LR_PROCUREMENT_LEGAL_DELAY",
            "loss_reason": "Procurement/legal delay",
            "loss_reason_category": "Timing",
            "controllable_flag": 0,
        },
    ]

    loss_reasons = pd.DataFrame(records)[EXPECTED_LOSS_REASON_COLUMNS]
    return loss_reasons


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def choose_existing_accounts(
    accounts: pd.DataFrame,
    n: int,
    rng: np.random.Generator,
    account_status_filter: set[str] | None = None,
) -> pd.DataFrame:
    """Sample accounts that can support non-lead opportunities."""
    eligible = accounts[
        accounts["account_id"].notna()
        & accounts["owner_rep_id"].notna()
        & accounts["territory_id"].notna()
        & accounts["region"].notna()
        & accounts["segment"].notna()
    ].copy()

    if account_status_filter is not None:
        filtered = eligible[eligible["account_status"].isin(account_status_filter)].copy()
        if not filtered.empty:
            eligible = filtered

    if len(eligible) < n:
        return eligible.sample(n=n, replace=True, random_state=int(rng.integers(0, 1_000_000)))

    return eligible.sample(n=n, replace=False, random_state=int(rng.integers(0, 1_000_000)))


def account_id_from_lead(row: pd.Series) -> str | pd.NA:
    """Return the account ID associated with a converted lead opportunity."""
    if pd.notna(row.get("created_account_id")):
        return str(row["created_account_id"])
    if pd.notna(row.get("matched_account_id")):
        return str(row["matched_account_id"])
    if pd.notna(row.get("possible_account_id")):
        return str(row["possible_account_id"])
    return pd.NA


def account_or_lead_value(account_row: pd.Series, lead_row: pd.Series, column: str, lead_column: str | None = None) -> str:
    """Use account value when available, otherwise fall back to lead value."""
    account_value = account_row.get(column, pd.NA)
    if pd.notna(account_value):
        return str(account_value)

    lead_value = lead_row.get(lead_column or column, pd.NA)
    if pd.notna(lead_value):
        return str(lead_value)

    return "Unknown"


def seller_owner_for_account(
    account_row: pd.Series,
    reps: pd.DataFrame,
    rng: np.random.Generator,
) -> str:
    """Choose an opportunity owner from active seller reps in the account territory."""
    owner_rep_id = account_row.get("owner_rep_id", pd.NA)

    if pd.notna(owner_rep_id):
        owner = reps.loc[reps["rep_id"] == str(owner_rep_id)]
        if not owner.empty and owner.iloc[0]["role"] in SELLER_ROLES and int(owner.iloc[0]["active_flag"]) == 1:
            return str(owner_rep_id)

    territory_id = str(account_row["territory_id"])
    segment = str(account_row["segment"])
    candidates = reps[
        (reps["territory_id"] == territory_id)
        & (reps["active_flag"] == 1)
        & (reps["role"].isin(SELLER_ROLES))
    ].copy()

    if candidates.empty:
        raise ValueError(f"No active seller reps found for account territory {territory_id}")

    if segment == "Enterprise":
        enterprise_candidates = candidates[candidates["role"] == "Enterprise Account Executive"]
        if not enterprise_candidates.empty:
            candidates = enterprise_candidates
    else:
        ae_candidates = candidates[candidates["role"] == "Account Executive"]
        if not ae_candidates.empty:
            candidates = ae_candidates

    chosen = candidates.iloc[int(rng.integers(0, len(candidates)))]
    return str(chosen["rep_id"])


def seller_owner_for_territory(
    territory_id: str,
    segment: str,
    reps: pd.DataFrame,
    rng: np.random.Generator,
) -> str:
    """Choose an active seller rep from a known territory."""
    candidates = reps[
        (reps["territory_id"] == str(territory_id))
        & (reps["active_flag"] == 1)
        & (reps["role"].isin(SELLER_ROLES))
    ].copy()

    if candidates.empty:
        raise ValueError(f"No active seller reps found for territory {territory_id}")

    if segment == "Enterprise":
        enterprise_candidates = candidates[candidates["role"] == "Enterprise Account Executive"]
        if not enterprise_candidates.empty:
            candidates = enterprise_candidates
    else:
        ae_candidates = candidates[candidates["role"] == "Account Executive"]
        if not ae_candidates.empty:
            candidates = ae_candidates

    chosen = candidates.iloc[int(rng.integers(0, len(candidates)))]
    return str(chosen["rep_id"])


def seller_owner_for_lead(
    lead_row: pd.Series,
    account_row: pd.Series,
    reps: pd.DataFrame,
    rng: np.random.Generator,
) -> str:
    """Choose an opportunity owner for a converted lead.

    Prefer the lead assigned seller when the lead owner is an AE/EAE. If the lead
    owner is an SDR, fall back to the account owner. If the account has no valid
    owner because it is a data-quality exception, use the lead's assigned
    territory and segment to choose an active seller.
    """
    assigned_rep_id = lead_row.get("assigned_rep_id", pd.NA)

    if pd.notna(assigned_rep_id):
        assigned = reps.loc[reps["rep_id"] == str(assigned_rep_id)]
        if not assigned.empty and assigned.iloc[0]["role"] in SELLER_ROLES and int(assigned.iloc[0]["active_flag"]) == 1:
            return str(assigned_rep_id)

    try:
        return seller_owner_for_account(account_row, reps, rng)
    except ValueError:
        territory_id = lead_row.get("assigned_territory_id", pd.NA)
        segment = lead_row.get("segment", pd.NA)
        if pd.notna(territory_id) and pd.notna(segment):
            return seller_owner_for_territory(str(territory_id), str(segment), reps, rng)
        raise


def choose_created_at_from_lead(lead_row: pd.Series, rng: np.random.Generator) -> pd.Timestamp:
    """Create opportunity date from lead first-touch or lead creation date."""
    first_touch = normalize_date(lead_row.get("first_touch_at"))
    lead_created = normalize_date(lead_row.get("created_at"))

    anchor = first_touch if pd.notna(first_touch) else lead_created
    lag_days = int(rng.integers(0, 15))
    return anchor + pd.Timedelta(days=lag_days)


def choose_random_created_at(rng: np.random.Generator) -> pd.Timestamp:
    """Generate a random opportunity creation date aligned to v0.1 lead date range."""
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2025-06-30")
    day_offset = int(rng.integers(0, (end - start).days + 1))
    return start + pd.Timedelta(days=day_offset)


def amount_for_segment(segment: str, source: str, rng: np.random.Generator) -> int:
    """Generate opportunity amount by segment and source."""
    if segment == "Enterprise":
        low, high = 150_000, 1_200_000
    elif segment == "Mid-Market":
        low, high = 45_000, 300_000
    elif segment == "Commercial":
        low, high = 8_000, 90_000
    else:
        low, high = 4_000, 40_000

    amount = float(rng.triangular(low, (low + high) / 2, high))

    if source == "expansion":
        amount *= float(rng.uniform(0.80, 1.45))
    elif source == "sales_generated":
        amount *= float(rng.uniform(0.90, 1.25))
    else:
        amount *= float(rng.uniform(0.75, 1.15))

    return int(round(amount / 1000) * 1000)


def activity_profile(
    opportunity_source: str,
    source_score: float,
    rng: np.random.Generator,
) -> tuple[int, int, int]:
    """Return activity_count, days_since_last_activity, next_step_exists."""
    if opportunity_source == "expansion":
        base_activities = rng.poisson(9)
    elif opportunity_source == "sales_generated":
        base_activities = rng.poisson(7)
    else:
        base_activities = rng.poisson(6)

    if source_score > 0.60:
        base_activities += int(rng.integers(2, 7))
    elif source_score < 0.30:
        base_activities -= int(rng.integers(0, 4))

    activity_count = int(max(0, base_activities))

    if activity_count == 0:
        days_since_last_activity = int(rng.integers(21, 91))
        next_step_exists = 0
    else:
        if source_score > 0.65:
            days_since_last_activity = int(rng.integers(0, 14))
            next_step_exists = int(rng.random() < 0.88)
        elif source_score > 0.40:
            days_since_last_activity = int(rng.integers(3, 31))
            next_step_exists = int(rng.random() < 0.68)
        else:
            days_since_last_activity = int(rng.integers(14, 75))
            next_step_exists = int(rng.random() < 0.40)

    return activity_count, days_since_last_activity, next_step_exists


def sales_cycle_days_for_segment(segment: str, stage: str, source_score: float, rng: np.random.Generator) -> int | pd.NA:
    """Generate sales cycle days for closed opportunities; blank for open opportunities."""
    if stage not in {"Closed Won", "Closed Lost"}:
        return pd.NA

    base = {
        "Enterprise": 95,
        "Mid-Market": 65,
        "Commercial": 38,
        "SMB": 25,
    }.get(segment, 45)

    if stage == "Closed Lost":
        base *= 0.85

    adjustment = (0.55 - source_score) * 25
    value = rng.normal(base + adjustment, 18)
    return int(max(7, round(value)))


def current_stage_for_open(segment: str, source_score: float, rng: np.random.Generator) -> str:
    """Choose a current open stage."""
    if source_score > 0.70:
        probs = [0.08, 0.18, 0.28, 0.28, 0.18]
    elif source_score > 0.40:
        probs = [0.20, 0.30, 0.25, 0.17, 0.08]
    else:
        probs = [0.38, 0.30, 0.18, 0.10, 0.04]

    return str(rng.choice(STAGE_ORDER, p=probs))


def days_in_stage(stage: str, source_score: float, rng: np.random.Generator) -> int:
    """Generate current days in stage."""
    benchmark = STAGE_BENCHMARK_DAYS.get(stage, 21)

    if stage in {"Closed Won", "Closed Lost"}:
        return int(rng.integers(0, 3))

    if source_score > 0.65:
        value = rng.normal(benchmark * 0.65, 6)
    elif source_score > 0.35:
        value = rng.normal(benchmark, 10)
    else:
        value = rng.normal(benchmark * 1.65, 14)

    return int(max(1, round(value)))


def speed_risk(speed_bucket: Any) -> int:
    """Risk points from speed-to-lead bucket."""
    if pd.isna(speed_bucket):
        return 0
    if speed_bucket in {"1-3 days", "4+ days", "No touch"}:
        return 2
    if speed_bucket == "Same day":
        return 1
    return 0


def routing_risk(routing_status: Any) -> int:
    """Risk points from routing outcome."""
    if pd.isna(routing_status):
        return 0
    if routing_status in {"manual_review", "fallback_queue", "failed_routing"}:
        return 2
    if routing_status == "routed_after_enrichment":
        return 1
    return 0


def data_quality_risk(data_quality_tier: Any) -> int:
    """Risk points from lead data quality."""
    if pd.isna(data_quality_tier):
        return 0
    if data_quality_tier == "poor":
        return 2
    if data_quality_tier == "partial":
        return 1
    return 0


def calculate_operational_risk_score(
    lead_row: pd.Series | None,
    rep_capacity_score: float | pd.NA,
    stage: str,
    days_stage: int,
    activity_count: int,
    days_since_activity: int,
    next_step_exists: int,
) -> int:
    """Calculate an operational-risk score from already-discussed risk signals."""
    score = 0

    if lead_row is not None:
        score += routing_risk(lead_row.get("routing_status"))
        score += speed_risk(lead_row.get("speed_to_lead_bucket"))
        score += data_quality_risk(lead_row.get("data_quality_tier"))

    if pd.notna(rep_capacity_score) and float(rep_capacity_score) > 90:
        score += 1

    if next_step_exists == 0:
        score += 1

    if days_since_activity > 14:
        score += 1

    if activity_count <= 2:
        score += 1

    benchmark = STAGE_BENCHMARK_DAYS.get(stage, 21)
    if benchmark > 0 and days_stage > benchmark:
        score += 1

    return int(min(score, 9))


def source_score_for_outcome(
    opportunity_source: str,
    lead_row: pd.Series | None,
    account_row: pd.Series,
    rep_capacity_score: float | pd.NA,
    rng: np.random.Generator,
) -> float:
    """Score opportunity quality before assigning outcomes."""
    score = 0.45

    if opportunity_source == "expansion":
        score += 0.14
    elif opportunity_source == "sales_generated":
        score += 0.05

    account_fit = account_row.get("account_fit_score", 50)
    if pd.notna(account_fit):
        score += (float(account_fit) - 50) / 250

    if lead_row is not None:
        score += (float(lead_row.get("lead_score", 50)) - 50) / 180
        score += {
            "Demo Request": 0.13,
            "Partner Referral": 0.10,
            "Paid Search": 0.04,
            "Free Trial / Free Sample": 0.03,
            "Webinar": 0.00,
            "Event Scan": -0.02,
            "Content Download": -0.06,
            "Other / Unknown": -0.08,
        }.get(str(lead_row.get("lead_source")), 0.0)
        score -= 0.06 * routing_risk(lead_row.get("routing_status"))
        score -= 0.05 * speed_risk(lead_row.get("speed_to_lead_bucket"))
        score -= 0.04 * data_quality_risk(lead_row.get("data_quality_tier"))

    if pd.notna(rep_capacity_score) and float(rep_capacity_score) > 90:
        score -= 0.06

    score += float(rng.normal(0, 0.08))
    return float(np.clip(score, 0.02, 0.98))


def choose_loss_reason(
    opportunity: dict[str, Any],
    loss_reasons: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.Series:
    """Choose a Closed-Lost reason based on operational risk."""
    risk = int(opportunity["operational_risk_score"])

    if risk >= 4:
        weights = {
            "LR_SLOW_FOLLOW_UP": 0.18,
            "LR_UNRESPONSIVE": 0.18,
            "LR_MISSING_DECISION_MAKER": 0.14,
            "LR_DUPLICATE_BAD_DATA": 0.13,
            "LR_TERRITORY_CONFUSION": 0.10,
            "LR_POOR_FIT": 0.10,
            "LR_NO_DECISION": 0.07,
            "LR_COMPETITOR_SELECTED": 0.05,
            "LR_TIMING": 0.03,
            "LR_PRICE": 0.02,
        }
    elif risk >= 2:
        weights = {
            "LR_UNRESPONSIVE": 0.14,
            "LR_NO_DECISION": 0.13,
            "LR_POOR_FIT": 0.12,
            "LR_SLOW_FOLLOW_UP": 0.11,
            "LR_MISSING_DECISION_MAKER": 0.10,
            "LR_COMPETITOR_SELECTED": 0.10,
            "LR_TIMING": 0.08,
            "LR_PRICE": 0.07,
            "LR_TECHNICAL_MISMATCH": 0.06,
            "LR_NO_BUDGET": 0.05,
            "LR_PROCUREMENT_LEGAL_DELAY": 0.04,
        }
    else:
        weights = {
            "LR_COMPETITOR_SELECTED": 0.18,
            "LR_NO_BUDGET": 0.15,
            "LR_PRICE": 0.13,
            "LR_TIMING": 0.12,
            "LR_NO_DECISION": 0.11,
            "LR_TECHNICAL_MISMATCH": 0.10,
            "LR_PROCUREMENT_LEGAL_DELAY": 0.08,
            "LR_POOR_FIT": 0.06,
            "LR_UNRESPONSIVE": 0.04,
            "LR_MISSING_DECISION_MAKER": 0.03,
        }

    ids = list(weights.keys())
    probs = np.array(list(weights.values()), dtype=float)
    probs = probs / probs.sum()
    loss_id = str(rng.choice(ids, p=probs))
    return loss_reasons.loc[loss_reasons["loss_reason_id"] == loss_id].iloc[0]


# -----------------------------------------------------------------------------
# Build opportunities
# -----------------------------------------------------------------------------


def build_opportunities(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build dim_loss_reasons and fact_opportunities."""
    rng = np.random.default_rng(seed)

    accounts = load_required_csv(ACCOUNTS_INPUT, "accounts")
    leads = load_required_csv(LEADS_INPUT, "leads")
    reps = load_required_csv(SALES_REPS_INPUT, "sales reps")
    loss_reasons = build_loss_reasons()

    rep_lookup = reps.set_index("rep_id")
    account_lookup = accounts.set_index("account_id")

    converted_leads = leads[
        (leads["converted_to_opportunity"] == 1)
        & leads["created_opportunity_id"].notna()
    ].copy()

    if len(converted_leads) != N_CONVERTED_MQL_OPPORTUNITIES:
        raise ValueError(
            f"Expected {N_CONVERTED_MQL_OPPORTUNITIES} converted opportunity leads; found {len(converted_leads)}."
        )

    records: list[dict[str, Any]] = []

    # 1. Converted-MQL opportunities from fact_leads.
    for _, lead_row in converted_leads.sort_values("created_opportunity_id").iterrows():
        account_id = account_id_from_lead(lead_row)
        if pd.isna(account_id) or str(account_id) not in account_lookup.index:
            raise ValueError(f"Lead {lead_row['lead_id']} has no valid account for opportunity creation.")

        account_row = account_lookup.loc[str(account_id)]
        owner_rep_id = seller_owner_for_lead(lead_row, account_row, reps, rng)
        rep_capacity = float(rep_lookup.loc[owner_rep_id, "capacity_score"])
        opportunity_region = account_or_lead_value(account_row, lead_row, "region")
        opportunity_territory = account_or_lead_value(account_row, lead_row, "territory_id", "assigned_territory_id")
        opportunity_segment = account_or_lead_value(account_row, lead_row, "segment")
        if opportunity_segment == "SMB":
            opportunity_segment = "Commercial"
        opportunity_industry = account_or_lead_value(account_row, lead_row, "industry")
        source_quality = source_score_for_outcome("converted_mql", lead_row, account_row, rep_capacity, rng)
        activity_count, days_since_activity, next_step_exists = activity_profile("converted_mql", source_quality, rng)
        stage_for_risk = current_stage_for_open(str(account_row["segment"]), source_quality, rng)
        days_stage = days_in_stage(stage_for_risk, source_quality, rng)
        risk_score = calculate_operational_risk_score(
            lead_row=lead_row,
            rep_capacity_score=rep_capacity,
            stage=stage_for_risk,
            days_stage=days_stage,
            activity_count=activity_count,
            days_since_activity=days_since_activity,
            next_step_exists=next_step_exists,
        )

        records.append({
            "opportunity_id": str(lead_row["created_opportunity_id"]),
            "account_id": str(account_id),
            "originating_lead_id": str(lead_row["lead_id"]),
            "owner_rep_id": owner_rep_id,
            "created_at": choose_created_at_from_lead(lead_row, rng),
            "close_date": pd.NA,
            "stage": stage_for_risk,
            "amount": amount_for_segment(opportunity_segment, "converted_mql", rng),
            "is_closed": 0,
            "is_won": 0,
            "is_closed_lost": 0,
            "opportunity_source": "converted_mql",
            "lead_source": str(lead_row["lead_source"]),
            "region": opportunity_region,
            "territory_id": opportunity_territory,
            "segment": opportunity_segment,
            "industry": opportunity_industry,
            "sales_cycle_days": pd.NA,
            "loss_reason_id": pd.NA,
            "loss_reason": pd.NA,
            "loss_reason_category": pd.NA,
            "controllable_loss_flag": pd.NA,
            "days_in_stage": days_stage,
            "activity_count": activity_count,
            "days_since_last_activity": days_since_activity,
            "next_step_exists": next_step_exists,
            "operational_risk_score": risk_score,
            "_source_quality": source_quality,
        })

    next_opp_number = N_CONVERTED_MQL_OPPORTUNITIES + 1

    # 2. Sales-generated opportunities.
    sales_accounts = choose_existing_accounts(accounts, N_SALES_GENERATED_OPPORTUNITIES, rng)
    for _, account_row in sales_accounts.iterrows():
        owner_rep_id = seller_owner_for_account(account_row, reps, rng)
        rep_capacity = float(rep_lookup.loc[owner_rep_id, "capacity_score"])
        source_quality = source_score_for_outcome("sales_generated", None, account_row, rep_capacity, rng)
        activity_count, days_since_activity, next_step_exists = activity_profile("sales_generated", source_quality, rng)
        stage_for_risk = current_stage_for_open(str(account_row["segment"]), source_quality, rng)
        days_stage = days_in_stage(stage_for_risk, source_quality, rng)
        risk_score = calculate_operational_risk_score(
            lead_row=None,
            rep_capacity_score=rep_capacity,
            stage=stage_for_risk,
            days_stage=days_stage,
            activity_count=activity_count,
            days_since_activity=days_since_activity,
            next_step_exists=next_step_exists,
        )

        records.append({
            "opportunity_id": f"OPP_{next_opp_number:06d}",
            "account_id": str(account_row["account_id"]),
            "originating_lead_id": pd.NA,
            "owner_rep_id": owner_rep_id,
            "created_at": choose_random_created_at(rng),
            "close_date": pd.NA,
            "stage": stage_for_risk,
            "amount": amount_for_segment(str(account_row["segment"]), "sales_generated", rng),
            "is_closed": 0,
            "is_won": 0,
            "is_closed_lost": 0,
            "opportunity_source": "sales_generated",
            "lead_source": pd.NA,
            "region": str(account_row["region"]),
            "territory_id": str(account_row["territory_id"]),
            "segment": str(account_row["segment"]),
            "industry": str(account_row["industry"]),
            "sales_cycle_days": pd.NA,
            "loss_reason_id": pd.NA,
            "loss_reason": pd.NA,
            "loss_reason_category": pd.NA,
            "controllable_loss_flag": pd.NA,
            "days_in_stage": days_stage,
            "activity_count": activity_count,
            "days_since_last_activity": days_since_activity,
            "next_step_exists": next_step_exists,
            "operational_risk_score": risk_score,
            "_source_quality": source_quality,
        })
        next_opp_number += 1

    # 3. Expansion opportunities.
    expansion_accounts = choose_existing_accounts(accounts, N_EXPANSION_OPPORTUNITIES, rng, {"customer"})
    for _, account_row in expansion_accounts.iterrows():
        owner_rep_id = seller_owner_for_account(account_row, reps, rng)
        rep_capacity = float(rep_lookup.loc[owner_rep_id, "capacity_score"])
        source_quality = source_score_for_outcome("expansion", None, account_row, rep_capacity, rng)
        activity_count, days_since_activity, next_step_exists = activity_profile("expansion", source_quality, rng)
        stage_for_risk = current_stage_for_open(str(account_row["segment"]), source_quality, rng)
        days_stage = days_in_stage(stage_for_risk, source_quality, rng)
        risk_score = calculate_operational_risk_score(
            lead_row=None,
            rep_capacity_score=rep_capacity,
            stage=stage_for_risk,
            days_stage=days_stage,
            activity_count=activity_count,
            days_since_activity=days_since_activity,
            next_step_exists=next_step_exists,
        )

        records.append({
            "opportunity_id": f"OPP_{next_opp_number:06d}",
            "account_id": str(account_row["account_id"]),
            "originating_lead_id": pd.NA,
            "owner_rep_id": owner_rep_id,
            "created_at": choose_random_created_at(rng),
            "close_date": pd.NA,
            "stage": stage_for_risk,
            "amount": amount_for_segment(str(account_row["segment"]), "expansion", rng),
            "is_closed": 0,
            "is_won": 0,
            "is_closed_lost": 0,
            "opportunity_source": "expansion",
            "lead_source": pd.NA,
            "region": str(account_row["region"]),
            "territory_id": str(account_row["territory_id"]),
            "segment": str(account_row["segment"]),
            "industry": str(account_row["industry"]),
            "sales_cycle_days": pd.NA,
            "loss_reason_id": pd.NA,
            "loss_reason": pd.NA,
            "loss_reason_category": pd.NA,
            "controllable_loss_flag": pd.NA,
            "days_in_stage": days_stage,
            "activity_count": activity_count,
            "days_since_last_activity": days_since_activity,
            "next_step_exists": next_step_exists,
            "operational_risk_score": risk_score,
            "_source_quality": source_quality,
        })
        next_opp_number += 1

    opportunities = pd.DataFrame(records)

    if len(opportunities) != N_OPPORTUNITIES:
        raise ValueError(f"Expected {N_OPPORTUNITIES} opportunities; found {len(opportunities)}.")

    # Assign outcomes by quality score so outcomes are plausible but target counts are exact.
    opportunities["_outcome_score"] = (
        opportunities["_source_quality"].astype(float)
        - opportunities["operational_risk_score"].astype(float) * 0.045
        + rng.normal(0, 0.06, len(opportunities))
    )

    outcome_targets_by_source = {
        "converted_mql": {"won": 310, "lost": 500, "open": 490},
        "sales_generated": {"won": 40, "lost": 240, "open": 70},
        "expansion": {"won": 50, "lost": 60, "open": 40},
    }

    won_indices_list: list[int] = []
    lost_indices_list: list[int] = []
    open_indices_list: list[int] = []

    for source, targets in outcome_targets_by_source.items():
        source_rows = opportunities[opportunities["opportunity_source"] == source]
        sorted_indices = source_rows.sort_values("_outcome_score", ascending=False).index.to_numpy()

        if len(sorted_indices) != sum(targets.values()):
            raise ValueError(f"Outcome targets for {source} do not match source row count.")

        source_won = sorted_indices[:targets["won"]]
        remaining = sorted_indices[targets["won"]:]
        source_lost = remaining[-targets["lost"]:]
        source_open = np.array([idx for idx in remaining if idx not in set(source_lost)])

        won_indices_list.extend(source_won.tolist())
        lost_indices_list.extend(source_lost.tolist())
        open_indices_list.extend(source_open.tolist())

    won_indices = np.array(won_indices_list)
    lost_indices = np.array(lost_indices_list)
    open_indices = np.array(open_indices_list)

    if len(won_indices) != CLOSED_WON_TARGET:
        raise ValueError(f"Expected {CLOSED_WON_TARGET} Closed-Won opportunities; found {len(won_indices)}.")
    if len(lost_indices) != CLOSED_LOST_TARGET:
        raise ValueError(f"Expected {CLOSED_LOST_TARGET} Closed-Lost opportunities; found {len(lost_indices)}.")
    if len(open_indices) != OPEN_TARGET:
        raise ValueError(f"Expected {OPEN_TARGET} open opportunities; found {len(open_indices)}.")

    opportunities.loc[won_indices, "stage"] = "Closed Won"
    opportunities.loc[won_indices, "is_closed"] = 1
    opportunities.loc[won_indices, "is_won"] = 1
    opportunities.loc[won_indices, "is_closed_lost"] = 0

    opportunities.loc[lost_indices, "stage"] = "Closed Lost"
    opportunities.loc[lost_indices, "is_closed"] = 1
    opportunities.loc[lost_indices, "is_won"] = 0
    opportunities.loc[lost_indices, "is_closed_lost"] = 1

    opportunities.loc[open_indices, "is_closed"] = 0
    opportunities.loc[open_indices, "is_won"] = 0
    opportunities.loc[open_indices, "is_closed_lost"] = 0

    # Sales cycle and close date for closed opportunities.
    for idx in np.concatenate([won_indices, lost_indices]):
        row = opportunities.loc[idx]
        cycle = sales_cycle_days_for_segment(str(row["segment"]), str(row["stage"]), float(row["_source_quality"]), rng)
        opportunities.loc[idx, "sales_cycle_days"] = cycle
        opportunities.loc[idx, "close_date"] = normalize_date(row["created_at"]) + pd.Timedelta(days=int(cycle))
        opportunities.loc[idx, "days_in_stage"] = int(rng.integers(0, 3))
        opportunities.loc[idx, "days_since_last_activity"] = int(rng.integers(0, 7))
        opportunities.loc[idx, "next_step_exists"] = 0

    # Loss reasons for Closed-Lost opportunities.
    for idx in lost_indices:
        loss = choose_loss_reason(opportunities.loc[idx].to_dict(), loss_reasons, rng)
        opportunities.loc[idx, "loss_reason_id"] = loss["loss_reason_id"]
        opportunities.loc[idx, "loss_reason"] = loss["loss_reason"]
        opportunities.loc[idx, "loss_reason_category"] = loss["loss_reason_category"]
        opportunities.loc[idx, "controllable_loss_flag"] = int(loss["controllable_flag"])

    # Leave non-lost loss fields empty.
    not_lost = opportunities["is_closed_lost"] == 0
    opportunities.loc[not_lost, [
        "loss_reason_id",
        "loss_reason",
        "loss_reason_category",
        "controllable_loss_flag",
    ]] = pd.NA

    # Clean output types and dates.
    opportunities["created_at"] = pd.to_datetime(opportunities["created_at"]).dt.date
    opportunities["close_date"] = pd.to_datetime(opportunities["close_date"], errors="coerce").dt.date
    opportunities["amount"] = opportunities["amount"].astype(int)
    for col in ["is_closed", "is_won", "is_closed_lost", "activity_count", "days_since_last_activity", "next_step_exists", "operational_risk_score"]:
        opportunities[col] = opportunities[col].astype(int)

    opportunities["sales_cycle_days"] = pd.to_numeric(opportunities["sales_cycle_days"], errors="coerce").astype("Int64")
    opportunities["days_in_stage"] = pd.to_numeric(opportunities["days_in_stage"], errors="coerce").astype("Int64")

    opportunities = opportunities[EXPECTED_OPPORTUNITY_COLUMNS]
    return loss_reasons, opportunities


# -----------------------------------------------------------------------------
# Validation and output
# -----------------------------------------------------------------------------


def validate_loss_reasons(loss_reasons: pd.DataFrame) -> None:
    """Validate dim_loss_reasons."""
    errors: list[str] = []

    if list(loss_reasons.columns) != EXPECTED_LOSS_REASON_COLUMNS:
        errors.append("Unexpected dim_loss_reasons columns or column order.")

    if loss_reasons["loss_reason_id"].duplicated().any():
        errors.append("Duplicate loss_reason_id values found.")

    if not set(loss_reasons["controllable_flag"]).issubset({0, 1}):
        errors.append("controllable_flag must contain only 0/1.")

    if errors:
        raise ValueError("dim_loss_reasons validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    print("Validation passed: dim_loss_reasons is valid.")


def validate_opportunities(opportunities: pd.DataFrame, loss_reasons: pd.DataFrame) -> None:
    """Validate fact_opportunities."""
    errors: list[str] = []

    accounts = load_required_csv(ACCOUNTS_INPUT, "accounts")
    leads = load_required_csv(LEADS_INPUT, "leads")
    reps = load_required_csv(SALES_REPS_INPUT, "sales reps")

    if list(opportunities.columns) != EXPECTED_OPPORTUNITY_COLUMNS:
        errors.append("Unexpected fact_opportunities columns or column order.")

    if len(opportunities) != N_OPPORTUNITIES:
        errors.append(f"Expected {N_OPPORTUNITIES} opportunities, found {len(opportunities)}.")

    if opportunities["opportunity_id"].duplicated().any():
        errors.append("Duplicate opportunity_id values found.")

    if opportunities["opportunity_id"].isna().any():
        errors.append("Null opportunity_id values found.")

    if opportunities["account_id"].isna().any():
        errors.append("Null account_id values found.")

    account_ids = set(accounts["account_id"].dropna().astype(str))
    missing_accounts = sorted(set(opportunities["account_id"].dropna().astype(str)) - account_ids)
    if missing_accounts:
        errors.append(f"account_id values missing from dim_accounts: {missing_accounts[:10]}")

    seller_reps = reps[
        reps["role"].isin(SELLER_ROLES)
        & (reps["active_flag"] == 1)
    ]
    seller_rep_ids = set(seller_reps["rep_id"].dropna().astype(str))
    missing_reps = sorted(set(opportunities["owner_rep_id"].dropna().astype(str)) - seller_rep_ids)
    if missing_reps:
        errors.append(f"owner_rep_id values missing from active seller reps: {missing_reps[:10]}")

    converted_leads = leads[(leads["converted_to_opportunity"] == 1) & leads["created_opportunity_id"].notna()].copy()
    converted_pairs = set(zip(
        converted_leads["created_opportunity_id"].astype(str),
        converted_leads["lead_id"].astype(str),
    ))
    opp_pairs = set(zip(
        opportunities.loc[opportunities["opportunity_source"] == "converted_mql", "opportunity_id"].astype(str),
        opportunities.loc[opportunities["opportunity_source"] == "converted_mql", "originating_lead_id"].astype(str),
    ))
    if opp_pairs != converted_pairs:
        errors.append("Converted-MQL opportunities do not exactly match fact_leads created_opportunity_id / lead_id pairs.")

    non_mql_lead_ids = opportunities.loc[
        opportunities["opportunity_source"] != "converted_mql",
        "originating_lead_id",
    ].dropna()
    if not non_mql_lead_ids.empty:
        errors.append("Non-converted-MQL opportunities should not have originating_lead_id populated.")

    source_counts = opportunities["opportunity_source"].value_counts().to_dict()
    expected_sources = {
        "converted_mql": N_CONVERTED_MQL_OPPORTUNITIES,
        "sales_generated": N_SALES_GENERATED_OPPORTUNITIES,
        "expansion": N_EXPANSION_OPPORTUNITIES,
    }
    if source_counts != expected_sources:
        errors.append(f"Unexpected opportunity source counts: {source_counts}")

    outcome_counts = {
        "closed_won": int(opportunities["is_won"].sum()),
        "closed_lost": int(opportunities["is_closed_lost"].sum()),
        "open": int((opportunities["is_closed"] == 0).sum()),
    }
    expected_outcomes = {
        "closed_won": CLOSED_WON_TARGET,
        "closed_lost": CLOSED_LOST_TARGET,
        "open": OPEN_TARGET,
    }
    if outcome_counts != expected_outcomes:
        errors.append(f"Unexpected outcome counts: {outcome_counts}")

    lost_rows = opportunities[opportunities["is_closed_lost"] == 1]
    not_lost_rows = opportunities[opportunities["is_closed_lost"] == 0]

    if lost_rows["loss_reason_id"].isna().any():
        errors.append("Closed-Lost opportunities must have loss_reason_id populated.")

    valid_loss_ids = set(loss_reasons["loss_reason_id"])
    missing_loss_ids = sorted(set(lost_rows["loss_reason_id"].dropna().astype(str)) - valid_loss_ids)
    if missing_loss_ids:
        errors.append(f"loss_reason_id values missing from dim_loss_reasons: {missing_loss_ids[:10]}")

    if not_lost_rows["loss_reason_id"].notna().any():
        errors.append("Non-Closed-Lost opportunities should not have loss_reason_id populated.")

    if opportunities["operational_risk_score"].lt(0).any() or opportunities["operational_risk_score"].gt(9).any():
        errors.append("operational_risk_score must be between 0 and 9.")

    if errors:
        raise ValueError("fact_opportunities validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    print("Validation passed: fact_opportunities is valid.")


def print_summary(opportunities: pd.DataFrame, loss_reasons: pd.DataFrame) -> None:
    """Print summary useful for validation output."""
    print("\nTotal opportunities:", len(opportunities))

    print("\nOpportunity source counts:")
    print(opportunities["opportunity_source"].value_counts().to_string())

    print("\nStage counts:")
    print(opportunities["stage"].value_counts().to_string())

    print("\nOutcome counts:")
    outcomes = pd.Series({
        "closed_won": int(opportunities["is_won"].sum()),
        "closed_lost": int(opportunities["is_closed_lost"].sum()),
        "open": int((opportunities["is_closed"] == 0).sum()),
    })
    print(outcomes.to_string())

    print("\nRegion counts:")
    print(opportunities["region"].value_counts().sort_index().to_string())

    print("\nSegment counts:")
    print(opportunities["segment"].value_counts().to_string())

    print("\nClosed-Lost count by loss reason category:")
    lost = opportunities[opportunities["is_closed_lost"] == 1]
    print(lost["loss_reason_category"].value_counts().to_string())

    print("\nClosed-Lost count by controllable flag:")
    print(lost["controllable_loss_flag"].value_counts(dropna=False).to_string())

    print("\nClosed-Lost amount by loss reason category:")
    amount_by_loss_category = lost.groupby("loss_reason_category")["amount"].sum().sort_values(ascending=False)
    print(amount_by_loss_category.to_string())

    print("\nClosed-Lost rate by operational risk score:")
    risk_summary = opportunities.groupby("operational_risk_score").agg(
        opportunities=("opportunity_id", "count"),
        closed_lost=("is_closed_lost", "sum"),
    )
    risk_summary["closed_lost_rate"] = (risk_summary["closed_lost"] / risk_summary["opportunities"]).round(3)
    print(risk_summary.to_string())

    print("\nClosed-Lost rate by opportunity source:")
    source_summary = opportunities.groupby("opportunity_source").agg(
        opportunities=("opportunity_id", "count"),
        closed_lost=("is_closed_lost", "sum"),
        closed_won=("is_won", "sum"),
        amount=("amount", "sum"),
    )
    source_summary["closed_lost_rate"] = (source_summary["closed_lost"] / source_summary["opportunities"]).round(3)
    print(source_summary.to_string())

    print("\nLoss reason dimension:")
    print(loss_reasons.to_string(index=False))

    print("\nPreview:")
    print(opportunities.head(10).to_string(index=False))


def save_outputs(loss_reasons: pd.DataFrame, opportunities: pd.DataFrame) -> None:
    """Save generated outputs."""
    LOSS_REASONS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OPPORTUNITIES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    loss_reasons.to_csv(LOSS_REASONS_OUTPUT, index=False)
    opportunities.to_csv(OPPORTUNITIES_OUTPUT, index=False)

    print(f"\nSaved loss reasons to: {LOSS_REASONS_OUTPUT}")
    print(f"Saved opportunities to: {OPPORTUNITIES_OUTPUT}")


if __name__ == "__main__":
    dim_loss_reasons_df, fact_opportunities_df = build_opportunities()
    validate_loss_reasons(dim_loss_reasons_df)
    validate_opportunities(fact_opportunities_df, dim_loss_reasons_df)
    print_summary(fact_opportunities_df, dim_loss_reasons_df)
    save_outputs(dim_loss_reasons_df, fact_opportunities_df)
