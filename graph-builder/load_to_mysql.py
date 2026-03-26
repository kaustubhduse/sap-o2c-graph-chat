"""
Load all preprocessed entity CSVs into MySQL tables.
Run this ONCE to populate the database before using the NL-to-SQL pipeline.

Usage:
    cd graph-builder
    python load_to_mysql.py

Uses DB settings from o2c-app/backend/.env (same module as o2c-app/backend/nl-to-sql/db.py).
"""
import sys
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Dodge-AI root
GRAPH_BUILDER_DIR = Path(__file__).resolve().parent
O2C_BACKEND_DIR = PROJECT_ROOT / "o2c-app" / "backend"
NL_TO_SQL_DIR = O2C_BACKEND_DIR / "nl-to-sql"

if not (NL_TO_SQL_DIR / "db.py").is_file():
    raise RuntimeError(
        f"Expected nl-to-sql at {NL_TO_SQL_DIR} (missing db.py). "
        "Keep o2c-app/backend/nl-to-sql in the repo."
    )

load_dotenv(O2C_BACKEND_DIR / ".env")
load_dotenv(GRAPH_BUILDER_DIR / ".env")

sys.path.insert(0, str(NL_TO_SQL_DIR))
from db import (  # noqa: E402
    DB_HOST,
    DB_NAME,
    DB_PORT,
    get_server_sqlalchemy_uri,
    get_sqlalchemy_uri,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Path to entity CSVs
ENTITIES_DIR = PROJECT_ROOT / "data-processing" / "output" / "entities"

# Also load graph JSON if available
GRAPH_OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def main():
    # Step 1: Create database if it doesn't exist
    logger.info(f"Connecting to MySQL at {DB_HOST}:{DB_PORT}...")
    
    # Connect without database first to create it
    server_engine = create_engine(
        get_server_sqlalchemy_uri(),
        connect_args={"init_command": "SET SESSION sql_require_primary_key=0"},
    )
    
    with server_engine.connect() as conn:
        # Use backticks for database name with hyphens
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"))
        conn.commit()
        logger.info(f"Database `{DB_NAME}` ready")
    
    server_engine.dispose()

    # Step 2: Connect to the target database
    engine = create_engine(
        get_sqlalchemy_uri(),
        connect_args={"init_command": "SET SESSION sql_require_primary_key=0"},
    )

    # Step 3: Load each CSV into a table
    csv_files = sorted(ENTITIES_DIR.glob("*.csv"))
    if not csv_files:
        logger.error(f"No CSV files found in {ENTITIES_DIR}")
        sys.exit(1)

    logger.info(f"Found {len(csv_files)} CSV files in {ENTITIES_DIR}")
    logger.info("=" * 60)

    total_rows = 0
    for csv_path in csv_files:
        table_name = csv_path.stem  # e.g. "sales_order_headers"
        
        df = pd.read_csv(csv_path, dtype=str).fillna("")
        
        # Write to MySQL (replace if exists)
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000,
        )
        
        total_rows += len(df)
        logger.info(f"  ✓ {table_name}: {len(df)} rows, {len(df.columns)} columns")

    logger.info("=" * 60)
    logger.info(f"Done! Loaded {len(csv_files)} tables, {total_rows:,} total rows into `{DB_NAME}`")

    # Step 4: Verify
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        logger.info(f"Tables in database: {tables}")

    engine.dispose()


if __name__ == "__main__":
    main()
