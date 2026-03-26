"""
Database layer: loads all entity CSVs into an in-memory SQLite database.
"""
import sqlite3
import logging
import pandas as pd
from pathlib import Path
from config import ENTITIES_DIR, MAX_RESULT_ROWS

logger = logging.getLogger(__name__)

_connection = None


def get_connection():
    """Get or create the singleton SQLite in-memory connection."""
    global _connection
    if _connection is None:
        _connection = _init_db()
    return _connection


def _init_db():
    """Load all entity CSVs into SQLite in-memory database."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    csv_files = sorted(ENTITIES_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {ENTITIES_DIR}")

    for csv_path in csv_files:
        table_name = csv_path.stem  # e.g. "sales_order_headers"
        df = pd.read_csv(csv_path, dtype=str).fillna("")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        logger.info(f"  Loaded {table_name}: {len(df)} rows, {len(df.columns)} cols")

    logger.info(f"Database ready: {len(csv_files)} tables loaded")
    return conn


def run_query(sql, params=None):
    """
    Execute a SQL query and return results as list of dicts.
    Automatically limits to MAX_RESULT_ROWS.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Safety: add LIMIT if not present
    sql_upper = sql.strip().upper()
    if "LIMIT" not in sql_upper and sql_upper.startswith("SELECT"):
        sql = sql.rstrip(";") + f" LIMIT {MAX_RESULT_ROWS}"

    try:
        cursor.execute(sql, params or [])
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise ValueError(f"SQL execution error: {e}")


def get_table_names():
    """Return list of all table names in the database."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(table_name):
    """Return column info for a table."""
    conn = get_connection()
    cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
    return [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]


def get_sample_values(table_name, column_name, limit=3):
    """Return a few distinct sample values from a column."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"SELECT DISTINCT \"{column_name}\" FROM \"{table_name}\" "
            f"WHERE \"{column_name}\" != '' LIMIT {limit}"
        )
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []
