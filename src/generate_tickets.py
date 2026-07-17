"""
Generate synthetic Ticket/SLA fact and SLA-policy dimension tables for a GTM / RevOps portfolio project.

This script creates:
    data/processed/dim_sla_policy.csv
    data/processed/fact_tickets.csv

It uses the existing GTM foundation files when available:
    data/processed/dim_sales_reps.csv
    data/processed/dim_accounts.csv
    data/processed/fact_leads.csv
    data/processed/fact_opportunities.csv

Business purpose:
    Build the Ticket/SLA layer so the dashboard can analyze whether AI-assisted
    ticket triage reduced misrouting, reassignment delay, backlog age, and SLA
    breaches across Sales Ops, CRM Eng, and Order Ops support intake.

Run from the project root:
    python src/generate_tickets.py
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
N_TICKETS = 5_000
N_PRE_AI_TICKETS = 2_500
N_POST_AI_TICKETS = 2_500
AI_LAUNCH_DATE = pd.Timestamp("2024-10-01")

SALES_REPS_INPUT = Path("data/processed/dim_sales_reps.csv")
ACCOUNTS_INPUT = Path("data/processed/dim_accounts.csv")
LEADS_INPUT = Path("data/processed/fact_leads.csv")
OPPORTUNITIES_INPUT = Path("data/processed/fact_opportunities.csv")

SLA_POLICY_OUTPUT = Path("data/processed/dim_sla_policy.csv")
TICKETS_OUTPUT = Path("data/processed/fact_tickets.csv")

SUPPORT_TEAMS = ["Sales Ops", "CRM Eng", "Order Ops"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
TRIAGE_METHODS = {"manual_picklist", "ai_assisted"}

CATEGORY_TEAM_MAP = {
    "lead_routing": "Sales Ops",
    "territory_assignment": "Sales Ops",
    "account_ownership": "Sales Ops",
    "opportunity_update": "Sales Ops",
    "data_quality": "Sales Ops",
    "reporting_request": "Sales Ops",
    "forecasting_support": "Sales Ops",
    "user_access": "CRM Eng",
    "automation_bug": "CRM Eng",
    "field_sync_issue": "CRM Eng",
    "quote_order_issue": "Order Ops",
    "contracting_issue": "Order Ops",
}

CATEGORY_WEIGHTS = {
    "lead_routing": 0.14,
    "territory_assignment": 0.11,
    "account_ownership": 0.10,
    "opportunity_update": 0.08,
    "data_quality": 0.10,
    "reporting_request": 0.07,
    "forecasting_support": 0.05,
    "user_access": 0.08,
    "automation_bug": 0.08,
    "field_sync_issue": 0.06,
    "quote_order_issue": 0.08,
    "contracting_issue": 0.05,
}

REQUESTER_ROLE_WEIGHTS = {
    "sales_rep": 0.36,
    "sales_manager": 0.16,
    "sales_development": 0.14,
    "sales_ops": 0.08,
    "marketing_ops": 0.08,
    "finance": 0.06,
    "legal": 0.05,
    "customer_success": 0.07,
}

PRIORITY_WEIGHTS_BY_CATEGORY = {
    "lead_routing": {"P1": 0.10, "P2": 0.38, "P3": 0.40, "P4": 0.12},
    "territory_assignment": {"P1": 0.06, "P2": 0.34, "P3": 0.46, "P4": 0.14},
    "account_ownership": {"P1": 0.06, "P2": 0.32, "P3": 0.48, "P4": 0.14},
    "opportunity_update": {"P1": 0.04, "P2": 0.26, "P3": 0.50, "P4": 0.20},
    "data_quality": {"P1": 0.03, "P2": 0.22, "P3": 0.52, "P4": 0.23},
    "reporting_request": {"P1": 0.02, "P2": 0.15, "P3": 0.48, "P4": 0.35},
    "forecasting_support": {"P1": 0.08, "P2": 0.36, "P3": 0.42, "P4": 0.14},
    "user_access": {"P1": 0.08, "P2": 0.34, "P3": 0.42, "P4": 0.16},
    "automation_bug": {"P1": 0.14, "P2": 0.38, "P3": 0.36, "P4": 0.12},
    "field_sync_issue": {"P1": 0.10, "P2": 0.34, "P3": 0.42, "P4": 0.14},
    "quote_order_issue": {"P1": 0.12, "P2": 0.40, "P3": 0.36, "P4": 0.12},
    "contracting_issue": {"P1": 0.08, "P2": 0.34, "P3": 0.44, "P4": 0.14},
}

EXPECTED_SLA_POLICY_COLUMNS = [
    "sla_policy_id",
    "priority",
    "ticket_category",
    "owner_team",
    "target_resolution_hours",
    "target_first_action_hours",
]

EXPECTED_TICKET_COLUMNS = [
    "ticket_id",
    "created_at",
    "resolved_at",
    "ticket_category",
    "priority",
    "requester_role",
    "initial_team_selected",
    "final_owner_team",
    "triage_method",
    "ai_confidence_score",
    "reassignment_required",
    "reassignment_delay_hours",
    "hours_to_first_action",
    "hours_to_resolution",
    "sla_policy_id",
    "sla_target_hours",
    "sla_due_at",
    "sla_met",
    "sla_breached",
    "post_ai_launch",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def weighted_choice(options_dict: dict[str, float], rng: np.random.Generator) -> str:
    """Select one value from a weighted dictionary."""
    values = list(options_dict.keys())
    probabilities = np.array(list(options_dict.values()), dtype=float)
    probabilities = probabilities / probabilities.sum()
    return str(rng.choice(values, p=probabilities))


def random_dates(start_date: str, end_date: str, n: int, rng: np.random.Generator) -> list[pd.Timestamp]:
    """Generate n random timestamps between start_date and end_date."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    hours_between = int((end - start).total_seconds() // 3600)
    random_hours = rng.integers(0, hours_between + 1, size=n)
    random_minutes = rng.integers(0, 60, size=n)
    return [start + pd.Timedelta(hours=int(h), minutes=int(m)) for h, m in zip(random_hours, random_minutes)]


def load_optional_csv(path: Path, label: str) -> pd.DataFrame | None:
    """Load optional CSV used for context validation / summary."""
    if path.exists():
        df = pd.read_csv(path)
        print(f"Loaded {label} from: {path}")
        return df
    print(f"Optional {label} not found at: {path}")
    return None


# -----------------------------------------------------------------------------
# SLA policy
# -----------------------------------------------------------------------------


def build_sla_policy() -> pd.DataFrame:
    """Build dim_sla_policy for discussed priorities, categories, and owner teams."""
    resolution_hours = {
        "P1": 4,
        "P2": 24,
        "P3": 72,
        "P4": 120,
    }
    first_action_hours = {
        "P1": 1,
        "P2": 4,
        "P3": 8,
        "P4": 24,
    }

    records: list[dict[str, Any]] = []
    for category, owner_team in CATEGORY_TEAM_MAP.items():
        for priority in PRIORITIES:
            records.append({
                "sla_policy_id": f"SLA_{category.upper()}_{priority}",
                "priority": priority,
                "ticket_category": category,
                "owner_team": owner_team,
                "target_resolution_hours": resolution_hours[priority],
                "target_first_action_hours": first_action_hours[priority],
            })

    return pd.DataFrame(records)[EXPECTED_SLA_POLICY_COLUMNS]


# -----------------------------------------------------------------------------
# Ticket simulation logic
# -----------------------------------------------------------------------------


def manual_assignment_accuracy(category: str, priority: str) -> float:
    """Manual picklist assignment accuracy before AI launch."""
    base = {
        "lead_routing": 0.78,
        "territory_assignment": 0.74,
        "account_ownership": 0.72,
        "opportunity_update": 0.70,
        "data_quality": 0.64,
        "reporting_request": 0.76,
        "forecasting_support": 0.76,
        "user_access": 0.72,
        "automation_bug": 0.61,
        "field_sync_issue": 0.60,
        "quote_order_issue": 0.76,
        "contracting_issue": 0.70,
    }[category]
    if priority == "P1":
        base += 0.04
    elif priority == "P4":
        base -= 0.04
    return float(np.clip(base, 0.45, 0.90))


def ai_assignment_accuracy(category: str, priority: str) -> float:
    """AI-assisted assignment accuracy after launch."""
    base = {
        "lead_routing": 0.93,
        "territory_assignment": 0.91,
        "account_ownership": 0.90,
        "opportunity_update": 0.89,
        "data_quality": 0.88,
        "reporting_request": 0.92,
        "forecasting_support": 0.91,
        "user_access": 0.90,
        "automation_bug": 0.86,
        "field_sync_issue": 0.86,
        "quote_order_issue": 0.92,
        "contracting_issue": 0.88,
    }[category]
    if priority == "P1":
        base += 0.02
    elif priority == "P4":
        base -= 0.02
    return float(np.clip(base, 0.75, 0.98))


def choose_wrong_team(correct_team: str, rng: np.random.Generator) -> str:
    """Choose an incorrect team for misrouted tickets."""
    alternatives = [team for team in SUPPORT_TEAMS if team != correct_team]
    return str(rng.choice(alternatives))


def ai_confidence(correct_assignment: bool, category: str, rng: np.random.Generator) -> float:
    """Generate AI confidence score for post-launch tickets."""
    if correct_assignment:
        base = rng.beta(9, 2)
    else:
        base = rng.beta(4, 5)

    if category in {"automation_bug", "field_sync_issue", "data_quality"}:
        base -= 0.04

    return round(float(np.clip(base, 0.05, 0.99)), 3)


def category_complexity_multiplier(category: str) -> float:
    """Resolution-time multiplier by request category."""
    return {
        "lead_routing": 0.90,
        "territory_assignment": 1.10,
        "account_ownership": 1.00,
        "opportunity_update": 0.85,
        "data_quality": 1.20,
        "reporting_request": 1.15,
        "forecasting_support": 1.05,
        "user_access": 0.75,
        "automation_bug": 1.35,
        "field_sync_issue": 1.30,
        "quote_order_issue": 1.05,
        "contracting_issue": 1.15,
    }[category]


def team_load_multiplier(team: str, post_ai_launch: int) -> float:
    """Synthetic queue pressure by final owner team."""
    if team == "Sales Ops":
        return 1.10 if post_ai_launch else 1.18
    if team == "CRM Eng":
        return 1.18 if post_ai_launch else 1.25
    return 1.04 if post_ai_launch else 1.12


def reassignment_delay_hours(triage_method: str, priority: str, rng: np.random.Generator) -> float:
    """Delay caused by reassignment when the initial team was wrong."""
    if triage_method == "ai_assisted":
        low, high = (0.5, 8.0)
    else:
        low, high = (2.0, 32.0)

    if priority == "P1":
        high *= 0.45
    elif priority == "P4":
        high *= 1.25

    return round(float(rng.uniform(low, high)), 1)


def first_action_hours(
    target_first_action_hours: int,
    reassignment_required: int,
    reassignment_delay: float,
    triage_method: str,
    priority: str,
    rng: np.random.Generator,
) -> float:
    """Generate hours to first analyst action."""
    base_multiplier = rng.triangular(0.10, 0.45, 1.35)
    if triage_method == "ai_assisted":
        base_multiplier *= 0.82
    if priority == "P1":
        base_multiplier *= 0.70
    if reassignment_required:
        return round(float(target_first_action_hours * base_multiplier + reassignment_delay * 0.45), 1)
    return round(float(max(0.1, target_first_action_hours * base_multiplier)), 1)


def resolution_hours(
    target_resolution_hours: int,
    category: str,
    final_owner_team: str,
    reassignment_required: int,
    reassignment_delay: float,
    triage_method: str,
    priority: str,
    rng: np.random.Generator,
) -> float:
    """Generate total resolution hours."""
    if triage_method == "ai_assisted":
        base_ratio = rng.triangular(0.20, 0.44, 0.98)
    else:
        base_ratio = rng.triangular(0.25, 0.55, 1.15)

    if priority == "P1":
        base_ratio *= 0.82
    elif priority == "P4":
        base_ratio *= 1.08

    complexity = category_complexity_multiplier(category)
    team_load = team_load_multiplier(final_owner_team, int(triage_method == "ai_assisted"))
    total = target_resolution_hours * base_ratio * complexity * team_load

    if reassignment_required:
        total += reassignment_delay

    # Keep some residual miss risk after AI launch.
    if triage_method == "ai_assisted" and rng.random() < 0.04:
        total *= float(rng.uniform(1.15, 1.55))
    elif triage_method == "manual_picklist" and rng.random() < 0.08:
        total *= float(rng.uniform(1.15, 1.80))

    return round(float(max(0.2, total)), 1)


# -----------------------------------------------------------------------------
# Build tickets
# -----------------------------------------------------------------------------


def build_tickets(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build dim_sla_policy and fact_tickets."""
    rng = np.random.default_rng(seed)

    # Load existing files for context; the ticket table remains flat in this version.
    load_optional_csv(SALES_REPS_INPUT, "sales reps")
    load_optional_csv(ACCOUNTS_INPUT, "accounts")
    load_optional_csv(LEADS_INPUT, "leads")
    load_optional_csv(OPPORTUNITIES_INPUT, "opportunities")

    sla_policy = build_sla_policy()
    sla_lookup = sla_policy.set_index(["ticket_category", "priority"])

    pre_dates = random_dates("2024-01-01", "2024-09-30 23:59:00", N_PRE_AI_TICKETS, rng)
    post_dates = random_dates("2024-10-01", "2025-06-30 23:59:00", N_POST_AI_TICKETS, rng)
    created_dates = pre_dates + post_dates

    categories = [weighted_choice(CATEGORY_WEIGHTS, rng) for _ in range(N_TICKETS)]

    records: list[dict[str, Any]] = []
    for i in range(N_TICKETS):
        ticket_id = f"TICK_{i + 1:06d}"
        created_at = created_dates[i]
        post_ai_launch = int(created_at >= AI_LAUNCH_DATE)
        triage_method = "ai_assisted" if post_ai_launch else "manual_picklist"

        category = categories[i]
        final_owner_team = CATEGORY_TEAM_MAP[category]
        priority = weighted_choice(PRIORITY_WEIGHTS_BY_CATEGORY[category], rng)
        requester_role = weighted_choice(REQUESTER_ROLE_WEIGHTS, rng)

        policy = sla_lookup.loc[(category, priority)]
        sla_policy_id = str(policy["sla_policy_id"])
        target_resolution = int(policy["target_resolution_hours"])
        target_first_action = int(policy["target_first_action_hours"])

        if triage_method == "ai_assisted":
            accuracy = ai_assignment_accuracy(category, priority)
        else:
            accuracy = manual_assignment_accuracy(category, priority)

        assignment_correct = bool(rng.random() < accuracy)
        if assignment_correct:
            initial_team_selected = final_owner_team
        else:
            initial_team_selected = choose_wrong_team(final_owner_team, rng)

        reassignment_required = int(initial_team_selected != final_owner_team)
        reassignment_delay = (
            reassignment_delay_hours(triage_method, priority, rng)
            if reassignment_required
            else 0.0
        )

        confidence = (
            ai_confidence(assignment_correct, category, rng)
            if triage_method == "ai_assisted"
            else pd.NA
        )

        first_action = first_action_hours(
            target_first_action_hours=target_first_action,
            reassignment_required=reassignment_required,
            reassignment_delay=reassignment_delay,
            triage_method=triage_method,
            priority=priority,
            rng=rng,
        )

        hours_to_resolve = resolution_hours(
            target_resolution_hours=target_resolution,
            category=category,
            final_owner_team=final_owner_team,
            reassignment_required=reassignment_required,
            reassignment_delay=reassignment_delay,
            triage_method=triage_method,
            priority=priority,
            rng=rng,
        )

        resolved_at = created_at + pd.Timedelta(hours=float(hours_to_resolve))
        sla_due_at = created_at + pd.Timedelta(hours=target_resolution)
        sla_met = int(hours_to_resolve <= target_resolution)
        sla_breached = int(not sla_met)

        records.append({
            "ticket_id": ticket_id,
            "created_at": created_at,
            "resolved_at": resolved_at,
            "ticket_category": category,
            "priority": priority,
            "requester_role": requester_role,
            "initial_team_selected": initial_team_selected,
            "final_owner_team": final_owner_team,
            "triage_method": triage_method,
            "ai_confidence_score": confidence,
            "reassignment_required": reassignment_required,
            "reassignment_delay_hours": reassignment_delay,
            "hours_to_first_action": first_action,
            "hours_to_resolution": hours_to_resolve,
            "sla_policy_id": sla_policy_id,
            "sla_target_hours": target_resolution,
            "sla_due_at": sla_due_at,
            "sla_met": sla_met,
            "sla_breached": sla_breached,
            "post_ai_launch": post_ai_launch,
        })

    tickets = pd.DataFrame(records)[EXPECTED_TICKET_COLUMNS]

    # Clean output dates.
    for column in ["created_at", "resolved_at", "sla_due_at"]:
        tickets[column] = pd.to_datetime(tickets[column]).dt.strftime("%Y-%m-%d %H:%M:%S")

    return sla_policy, tickets


# -----------------------------------------------------------------------------
# Validation and output
# -----------------------------------------------------------------------------


def validate_sla_policy(sla_policy: pd.DataFrame) -> None:
    """Validate dim_sla_policy."""
    errors: list[str] = []

    if list(sla_policy.columns) != EXPECTED_SLA_POLICY_COLUMNS:
        errors.append("Unexpected dim_sla_policy columns or column order.")

    if sla_policy["sla_policy_id"].duplicated().any():
        errors.append("Duplicate sla_policy_id values found.")

    if not set(sla_policy["priority"]).issubset(set(PRIORITIES)):
        errors.append("Invalid priority values in dim_sla_policy.")

    if not set(sla_policy["ticket_category"]).issubset(set(CATEGORY_TEAM_MAP.keys())):
        errors.append("Invalid ticket_category values in dim_sla_policy.")

    if not set(sla_policy["owner_team"]).issubset(set(SUPPORT_TEAMS)):
        errors.append("Invalid owner_team values in dim_sla_policy.")

    if sla_policy["target_resolution_hours"].le(0).any():
        errors.append("target_resolution_hours must be positive.")

    if sla_policy["target_first_action_hours"].le(0).any():
        errors.append("target_first_action_hours must be positive.")

    if errors:
        raise ValueError("dim_sla_policy validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    print("Validation passed: dim_sla_policy is valid.")


def validate_tickets(tickets: pd.DataFrame, sla_policy: pd.DataFrame) -> None:
    """Validate fact_tickets."""
    errors: list[str] = []

    if list(tickets.columns) != EXPECTED_TICKET_COLUMNS:
        errors.append("Unexpected fact_tickets columns or column order.")

    if len(tickets) != N_TICKETS:
        errors.append(f"Expected {N_TICKETS} tickets, found {len(tickets)}.")

    if tickets["ticket_id"].duplicated().any():
        errors.append("Duplicate ticket_id values found.")

    required_columns = [
        "ticket_id",
        "created_at",
        "resolved_at",
        "ticket_category",
        "priority",
        "initial_team_selected",
        "final_owner_team",
        "triage_method",
        "hours_to_resolution",
        "sla_target_hours",
        "sla_met",
        "sla_breached",
        "post_ai_launch",
    ]
    for column in required_columns:
        if tickets[column].isna().any():
            errors.append(f"Null values found in required column: {column}")

    if not set(tickets["ticket_category"]).issubset(set(CATEGORY_TEAM_MAP.keys())):
        errors.append("Invalid ticket_category values found.")

    if not set(tickets["priority"]).issubset(set(PRIORITIES)):
        errors.append("Invalid priority values found.")

    if not set(tickets["initial_team_selected"]).issubset(set(SUPPORT_TEAMS)):
        errors.append("Invalid initial_team_selected values found.")

    if not set(tickets["final_owner_team"]).issubset(set(SUPPORT_TEAMS)):
        errors.append("Invalid final_owner_team values found.")

    if not set(tickets["triage_method"]).issubset(TRIAGE_METHODS):
        errors.append("Invalid triage_method values found.")

    if not set(tickets["sla_met"]).issubset({0, 1}):
        errors.append("sla_met must contain only 0/1.")

    if not set(tickets["sla_breached"]).issubset({0, 1}):
        errors.append("sla_breached must contain only 0/1.")

    if not set(tickets["reassignment_required"]).issubset({0, 1}):
        errors.append("reassignment_required must contain only 0/1.")

    if not set(tickets["post_ai_launch"]).issubset({0, 1}):
        errors.append("post_ai_launch must contain only 0/1.")

    calculated_reassignment = (tickets["initial_team_selected"] != tickets["final_owner_team"]).astype(int)
    if not (calculated_reassignment == tickets["reassignment_required"]).all():
        errors.append("reassignment_required must equal initial_team_selected != final_owner_team.")

    calculated_sla_met = (tickets["hours_to_resolution"] <= tickets["sla_target_hours"]).astype(int)
    if not (calculated_sla_met == tickets["sla_met"]).all():
        errors.append("sla_met must equal hours_to_resolution <= sla_target_hours.")

    if not ((1 - tickets["sla_met"]) == tickets["sla_breached"]).all():
        errors.append("sla_breached must equal 1 - sla_met.")

    created = pd.to_datetime(tickets["created_at"])
    resolved = pd.to_datetime(tickets["resolved_at"])
    due = pd.to_datetime(tickets["sla_due_at"])

    if (resolved < created).any():
        errors.append("resolved_at must be after created_at.")

    calculated_due = created + pd.to_timedelta(tickets["sla_target_hours"], unit="h")
    if not (calculated_due == due).all():
        errors.append("sla_due_at must equal created_at + sla_target_hours.")

    if int((tickets["triage_method"] == "manual_picklist").sum()) != N_PRE_AI_TICKETS:
        errors.append(f"Expected {N_PRE_AI_TICKETS} manual_picklist tickets.")

    if int((tickets["triage_method"] == "ai_assisted").sum()) != N_POST_AI_TICKETS:
        errors.append(f"Expected {N_POST_AI_TICKETS} ai_assisted tickets.")

    if tickets.loc[tickets["triage_method"] == "manual_picklist", "ai_confidence_score"].notna().any():
        errors.append("manual_picklist tickets should not have ai_confidence_score populated.")

    ai_scores = tickets.loc[tickets["triage_method"] == "ai_assisted", "ai_confidence_score"]
    if ai_scores.isna().any():
        errors.append("ai_assisted tickets must have ai_confidence_score populated.")
    elif ai_scores.lt(0).any() or ai_scores.gt(1).any():
        errors.append("ai_confidence_score must be between 0 and 1.")

    valid_sla_ids = set(sla_policy["sla_policy_id"])
    missing_sla_ids = sorted(set(tickets["sla_policy_id"].dropna().astype(str)) - valid_sla_ids)
    if missing_sla_ids:
        errors.append(f"sla_policy_id values missing from dim_sla_policy: {missing_sla_ids[:10]}")

    if errors:
        raise ValueError("fact_tickets validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    print("Validation passed: fact_tickets is valid.")


def print_summary(tickets: pd.DataFrame, sla_policy: pd.DataFrame) -> None:
    """Print summary useful for validation output."""
    print("\nTotal tickets:", len(tickets))

    print("\nTriage method counts:")
    print(tickets["triage_method"].value_counts().to_string())

    print("\nPost-AI launch counts:")
    print(tickets["post_ai_launch"].value_counts().sort_index().to_string())

    print("\nTicket category counts:")
    print(tickets["ticket_category"].value_counts().to_string())

    print("\nFinal owner team counts:")
    print(tickets["final_owner_team"].value_counts().to_string())

    print("\nPriority counts:")
    print(tickets["priority"].value_counts().sort_index().to_string())

    print("\nSLA performance by triage method:")
    triage_summary = tickets.groupby("triage_method").agg(
        tickets=("ticket_id", "count"),
        sla_met_rate=("sla_met", "mean"),
        sla_breach_rate=("sla_breached", "mean"),
        reassignment_rate=("reassignment_required", "mean"),
        avg_reassignment_delay_hours=("reassignment_delay_hours", "mean"),
        avg_hours_to_resolution=("hours_to_resolution", "mean"),
    )
    for column in ["sla_met_rate", "sla_breach_rate", "reassignment_rate", "avg_reassignment_delay_hours", "avg_hours_to_resolution"]:
        triage_summary[column] = triage_summary[column].round(3)
    print(triage_summary.to_string())

    print("\nSLA breach rate by final owner team and triage method:")
    team_summary = tickets.groupby(["final_owner_team", "triage_method"]).agg(
        tickets=("ticket_id", "count"),
        sla_breach_rate=("sla_breached", "mean"),
        reassignment_rate=("reassignment_required", "mean"),
    )
    team_summary["sla_breach_rate"] = team_summary["sla_breach_rate"].round(3)
    team_summary["reassignment_rate"] = team_summary["reassignment_rate"].round(3)
    print(team_summary.to_string())

    print("\nSLA breach rate by ticket category:")
    category_summary = tickets.groupby("ticket_category").agg(
        tickets=("ticket_id", "count"),
        sla_breach_rate=("sla_breached", "mean"),
        reassignment_rate=("reassignment_required", "mean"),
    ).sort_values("sla_breach_rate", ascending=False)
    category_summary["sla_breach_rate"] = category_summary["sla_breach_rate"].round(3)
    category_summary["reassignment_rate"] = category_summary["reassignment_rate"].round(3)
    print(category_summary.to_string())

    print("\nAI confidence bucket summary:")
    ai_tickets = tickets[tickets["triage_method"] == "ai_assisted"].copy()
    ai_tickets["ai_confidence_bucket"] = pd.cut(
        ai_tickets["ai_confidence_score"].astype(float),
        bins=[0.0, 0.5, 0.7, 0.85, 1.0],
        labels=["0.00-0.49", "0.50-0.69", "0.70-0.84", "0.85-1.00"],
        include_lowest=True,
    )
    ai_tickets["assignment_correct"] = (ai_tickets["initial_team_selected"] == ai_tickets["final_owner_team"]).astype(int)
    confidence_summary = ai_tickets.groupby("ai_confidence_bucket", observed=False).agg(
        tickets=("ticket_id", "count"),
        assignment_accuracy=("assignment_correct", "mean"),
        sla_met_rate=("sla_met", "mean"),
    )
    confidence_summary["assignment_accuracy"] = confidence_summary["assignment_accuracy"].round(3)
    confidence_summary["sla_met_rate"] = confidence_summary["sla_met_rate"].round(3)
    print(confidence_summary.to_string())

    print("\nSLA policy rows:", len(sla_policy))
    print("\nPreview:")
    print(tickets.head(10).to_string(index=False))


def save_outputs(sla_policy: pd.DataFrame, tickets: pd.DataFrame) -> None:
    """Save generated outputs."""
    SLA_POLICY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    TICKETS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sla_policy.to_csv(SLA_POLICY_OUTPUT, index=False)
    tickets.to_csv(TICKETS_OUTPUT, index=False)
    print(f"\nSaved SLA policy to: {SLA_POLICY_OUTPUT}")
    print(f"Saved tickets to: {TICKETS_OUTPUT}")


if __name__ == "__main__":
    dim_sla_policy_df, fact_tickets_df = build_tickets()
    validate_sla_policy(dim_sla_policy_df)
    validate_tickets(fact_tickets_df, dim_sla_policy_df)
    print_summary(fact_tickets_df, dim_sla_policy_df)
    save_outputs(dim_sla_policy_df, fact_tickets_df)
