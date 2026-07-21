from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


DB_PATH = Path("data/processed/gtm_ops.db")


st.set_page_config(
    page_title="GTM Operations Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def run_query(query: str) -> pd.DataFrame:
    """Run a SQL query against the local SQLite database and return a dataframe."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run: python src/build_database.py"
        )

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


def format_int(value: float | int) -> str:
    """Format numbers as whole-number strings."""
    return f"{int(value):,}"


def format_pct(value: float | int) -> str:
    """Format decimal rates as percentages."""
    return f"{float(value) * 100:.1f}%"


def format_money(value: float | int) -> str:
    """Format dollar values."""
    return f"${float(value):,.0f}"


def load_dashboard_data() -> dict[str, pd.DataFrame]:
    """Load all dashboard views from SQLite."""
    return {
        "lead_funnel": run_query("SELECT * FROM vw_lead_funnel_summary;"),
        "routing_failures": run_query("""
            SELECT *
            FROM vw_lead_routing_failures
            ORDER BY leads DESC;
        """),
        "speed_to_lead": run_query("""
            SELECT *
            FROM vw_conversion_by_speed_to_lead;
        """),
        "closed_lost": run_query("""
            SELECT *
            FROM vw_closed_lost_summary
            ORDER BY closed_lost_amount DESC;
        """),
        "risk": run_query("""
            SELECT *
            FROM vw_closed_lost_by_operational_risk
            ORDER BY operational_risk_score;
        """),
        "ticket_sla": run_query("""
            SELECT *
            FROM vw_ticket_sla_summary
            ORDER BY sla_breach_rate DESC;
        """),
        "ai_triage": run_query("""
            SELECT *
            FROM vw_ticket_ai_triage_impact
            ORDER BY triage_method;
        """),
    }


st.title("GTM Operations Intelligence Dashboard")
st.caption(
    "Synthetic RevOps analytics project using Python-generated GTM data, SQLite views, and Streamlit."
)

try:
    data = load_dashboard_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()


overview_tab, leads_tab, opps_tab, tickets_tab = st.tabs([
    "Executive Overview",
    "Lead Routing & Conversion",
    "Closed-Lost Opportunities",
    "Ticket SLA Operations",
])


with overview_tab:
    st.subheader("Executive Overview")

    lead_funnel = data["lead_funnel"].iloc[0]
    ai_triage = data["ai_triage"]

    total_leads = lead_funnel["total_leads"]
    mqls = lead_funnel["mqls"]
    opportunities = lead_funnel["converted_to_opportunity"]
    lead_to_opp_rate = lead_funnel["lead_to_opportunity_rate"]

    closed_lost = data["closed_lost"]
    closed_lost_amount = closed_lost["closed_lost_amount"].sum()

    manual = ai_triage[ai_triage["triage_method"] == "manual_picklist"].iloc[0]
    ai = ai_triage[ai_triage["triage_method"] == "ai_assisted"].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", format_int(total_leads))
    col2.metric("MQLs", format_int(mqls))
    col3.metric("Converted Opportunities", format_int(opportunities))
    col4.metric("Lead → Opportunity Rate", format_pct(lead_to_opp_rate))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Closed-Lost Amount", format_money(closed_lost_amount))
    col6.metric("Manual SLA Met Rate", format_pct(manual["sla_met_rate"]))
    col7.metric("AI SLA Met Rate", format_pct(ai["sla_met_rate"]))
    col8.metric(
        "Reassignment Rate Change",
        f"{format_pct(manual['reassignment_rate'])} → {format_pct(ai['reassignment_rate'])}",
    )

    st.markdown("### Lead Funnel")
    st.dataframe(data["lead_funnel"], use_container_width=True)

    st.markdown("### AI Triage Impact")
    st.dataframe(data["ai_triage"], use_container_width=True)


with leads_tab:
    st.subheader("Lead Routing & Conversion")

    speed_to_lead = data["speed_to_lead"].copy()
    routing_failures = data["routing_failures"].copy()

    st.markdown("### Conversion by Speed-to-Lead")
    st.dataframe(speed_to_lead, use_container_width=True)

    chart_df = speed_to_lead[[
        "speed_to_lead_bucket",
        "opportunity_conversion_rate",
    ]].set_index("speed_to_lead_bucket")

    st.bar_chart(chart_df)

    st.markdown("### Routing Failures")
    st.dataframe(routing_failures.head(25), use_container_width=True)

    failure_chart = (
        routing_failures.groupby("routing_status", as_index=False)["leads"]
        .sum()
        .sort_values("leads", ascending=False)
        .set_index("routing_status")
    )

    st.bar_chart(failure_chart)


with opps_tab:
    st.subheader("Closed-Lost Opportunities")

    closed_lost = data["closed_lost"].copy()
    risk = data["risk"].copy()

    st.markdown("### Closed-Lost Amount by Reason")
    st.dataframe(closed_lost, use_container_width=True)

    loss_chart = (
        closed_lost.groupby("loss_reason_category", as_index=False)["closed_lost_amount"]
        .sum()
        .sort_values("closed_lost_amount", ascending=False)
        .set_index("loss_reason_category")
    )

    st.bar_chart(loss_chart)

    st.markdown("### Closed-Lost Rate by Operational Risk Score")
    st.dataframe(risk, use_container_width=True)

    risk_chart = risk[[
        "operational_risk_score",
        "closed_lost_rate",
    ]].set_index("operational_risk_score")

    st.line_chart(risk_chart)


with tickets_tab:
    st.subheader("Ticket SLA Operations")

    ticket_sla = data["ticket_sla"].copy()
    ai_triage = data["ai_triage"].copy()

    st.markdown("### SLA Performance by Team, Category, and Priority")
    st.dataframe(ticket_sla, use_container_width=True)

    st.markdown("### SLA Breach Rate by Final Owner Team")
    team_chart = (
        ticket_sla.groupby("final_owner_team", as_index=False)
        .agg(sla_breach_rate=("sla_breach_rate", "mean"))
        .sort_values("sla_breach_rate", ascending=False)
        .set_index("final_owner_team")
    )

    st.bar_chart(team_chart)

    st.markdown("### Manual vs AI-Assisted Triage")
    st.dataframe(ai_triage, use_container_width=True)

    triage_chart = ai_triage[[
        "triage_method",
        "sla_met_rate",
        "reassignment_rate",
    ]].set_index("triage_method")

    st.bar_chart(triage_chart)