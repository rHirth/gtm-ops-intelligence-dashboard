from pathlib import Path
import sqlite3

import pandas as pd


DATA_DIR = Path("data/processed")
DB_PATH = DATA_DIR / "gtm_ops.db"
VIEWS_SQL_PATH = Path("sql/create_views.sql")

TABLE_FILES = {
    "dim_sales_reps": DATA_DIR / "dim_sales_reps.csv",
    "dim_accounts": DATA_DIR / "dim_accounts.csv",
    "fact_leads": DATA_DIR / "fact_leads.csv",
    "dim_loss_reasons": DATA_DIR / "dim_loss_reasons.csv",
    "fact_opportunities": DATA_DIR / "fact_opportunities.csv",
    "dim_sla_policy": DATA_DIR / "dim_sla_policy.csv",
    "fact_tickets": DATA_DIR / "fact_tickets.csv",
}


def create_views(conn: sqlite3.Connection) -> None:
    """Create dashboard-ready SQLite views."""
    if not VIEWS_SQL_PATH.exists():
        raise FileNotFoundError(f"Missing views SQL file: {VIEWS_SQL_PATH}")

    views_sql = VIEWS_SQL_PATH.read_text(encoding="utf-8")
    conn.executescript(views_sql)
    conn.commit()

    print("\nViews created.")

def print_views(conn: sqlite3.Connection) -> None:
    """Print views currently available in the SQLite database."""
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'view'
        ORDER BY name;
    """

    views = pd.read_sql_query(query, conn)

    print("\nSQLite views:")
    if views.empty:
        print("No views found.")
    else:
        for view_name in views["name"]:
            print(view_name)

def load_csv_to_sqlite(conn: sqlite3.Connection, table_name: str, csv_path: Path) -> None:
    """Load one CSV file into a SQLite table."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing required CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    print(f"Loaded {table_name}: {len(df):,} rows")


def print_row_counts(conn: sqlite3.Connection) -> None:
    """Print row counts from each SQLite table."""
    print("\nSQLite row counts:")

    for table_name in TABLE_FILES:
        query = f"SELECT COUNT(*) AS row_count FROM {table_name}"
        row_count = pd.read_sql_query(query, conn).iloc[0]["row_count"]
        print(f"{table_name}: {row_count:,}")

def run_validation_queries(conn: sqlite3.Connection) -> None:
    """Run basic relationship and row-count validation checks."""
    checks = {
        "accounts_missing_owner_reps": """
            SELECT COUNT(*) AS issue_count
            FROM dim_accounts a
            LEFT JOIN dim_sales_reps r
                ON a.owner_rep_id = r.rep_id
            WHERE a.owner_rep_id IS NOT NULL
              AND r.rep_id IS NULL;
        """,
        "leads_missing_assigned_reps": """
            SELECT COUNT(*) AS issue_count
            FROM fact_leads l
            LEFT JOIN dim_sales_reps r
                ON l.assigned_rep_id = r.rep_id
            WHERE l.assigned_rep_id IS NOT NULL
              AND r.rep_id IS NULL;
        """,
        "opportunities_missing_accounts": """
            SELECT COUNT(*) AS issue_count
            FROM fact_opportunities o
            LEFT JOIN dim_accounts a
                ON o.account_id = a.account_id
            WHERE a.account_id IS NULL;
        """,
        "opportunities_missing_owner_reps": """
            SELECT COUNT(*) AS issue_count
            FROM fact_opportunities o
            LEFT JOIN dim_sales_reps r
                ON o.owner_rep_id = r.rep_id
            WHERE o.owner_rep_id IS NOT NULL
              AND r.rep_id IS NULL;
        """,
        "tickets_missing_sla_policy": """
            SELECT COUNT(*) AS issue_count
            FROM fact_tickets t
            LEFT JOIN dim_sla_policy s
                ON t.sla_policy_id = s.sla_policy_id
            WHERE s.sla_policy_id IS NULL;
        """,
    }

    print("\nSQLite relationship checks:")

    for check_name, query in checks.items():
        result = pd.read_sql_query(query, conn)
        issue_count = int(result.iloc[0]["issue_count"])
        print(f"{check_name}: {issue_count}")

        if issue_count != 0:
            raise ValueError(f"Validation failed: {check_name} returned {issue_count}")

def create_indexes(conn: sqlite3.Connection) -> None:
    """Create useful indexes for dashboard queries."""
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_accounts_account_id ON dim_accounts(account_id);",
        "CREATE INDEX IF NOT EXISTS idx_accounts_owner_rep_id ON dim_accounts(owner_rep_id);",
        "CREATE INDEX IF NOT EXISTS idx_accounts_region ON dim_accounts(region);",

        "CREATE INDEX IF NOT EXISTS idx_leads_lead_id ON fact_leads(lead_id);",
        "CREATE INDEX IF NOT EXISTS idx_leads_assigned_rep_id ON fact_leads(assigned_rep_id);",
        "CREATE INDEX IF NOT EXISTS idx_leads_created_opportunity_id ON fact_leads(created_opportunity_id);",
        "CREATE INDEX IF NOT EXISTS idx_leads_region ON fact_leads(region);",
        "CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON fact_leads(lead_source);",

        "CREATE INDEX IF NOT EXISTS idx_opps_opportunity_id ON fact_opportunities(opportunity_id);",
        "CREATE INDEX IF NOT EXISTS idx_opps_account_id ON fact_opportunities(account_id);",
        "CREATE INDEX IF NOT EXISTS idx_opps_originating_lead_id ON fact_opportunities(originating_lead_id);",
        "CREATE INDEX IF NOT EXISTS idx_opps_owner_rep_id ON fact_opportunities(owner_rep_id);",
        "CREATE INDEX IF NOT EXISTS idx_opps_region ON fact_opportunities(region);",
        "CREATE INDEX IF NOT EXISTS idx_opps_stage ON fact_opportunities(stage);",

        "CREATE INDEX IF NOT EXISTS idx_tickets_ticket_id ON fact_tickets(ticket_id);",
        "CREATE INDEX IF NOT EXISTS idx_tickets_sla_policy_id ON fact_tickets(sla_policy_id);",
        "CREATE INDEX IF NOT EXISTS idx_tickets_triage_method ON fact_tickets(triage_method);",
        "CREATE INDEX IF NOT EXISTS idx_tickets_final_owner_team ON fact_tickets(final_owner_team);",
    ]

    for statement in index_statements:
        conn.execute(statement)

    conn.commit()
    print("\nIndexes created.")

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        for table_name, csv_path in TABLE_FILES.items():
            load_csv_to_sqlite(conn, table_name, csv_path)

        create_indexes(conn)
        create_views(conn)

        print_row_counts(conn)
        print_views(conn)
        run_validation_queries(conn)

    print(f"\nSaved SQLite database to: {DB_PATH}")


if __name__ == "__main__":
    main()