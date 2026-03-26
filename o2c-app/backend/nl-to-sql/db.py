"""
Database connection layer using LangChain's SQLDatabase and PyMySQL.
Connects to the MySQL database containing the SAP O2C tables.
"""
import os
import logging
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase

load_dotenv()
logger = logging.getLogger(__name__)

import urllib.parse
DB_USER = os.getenv("DB_USER", "root")
raw_password = os.getenv("DB_PASSWORD", "")
DB_PASSWORD = urllib.parse.quote_plus(raw_password)
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "db-1")

# Singleton
_db_instance = None


def get_db() -> SQLDatabase:
    """
    Return a singleton LangChain SQLDatabase connected to MySQL.
    Uses pymysql driver.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    uri = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logger.info(f"Connecting to MySQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    _db_instance = SQLDatabase.from_uri(
        uri,
        sample_rows_in_table_info=3,  # include sample rows for LLM context
    )

    tables = _db_instance.get_usable_table_names()
    logger.info(f"Connected. Found {len(tables)} tables: {tables}")
    return _db_instance


def get_table_names():
    """Return list of all table names."""
    return get_db().get_usable_table_names()


def get_table_info(tables=None):
    """
    Return CREATE TABLE + sample rows for specified tables.
    If tables is None, returns info for ALL tables.
    """
    db = get_db()
    if tables:
        return db.get_table_info(table_names=tables)
    return db.get_table_info()


def run_query(sql: str) -> str:
    """Execute SQL query and return results as string."""
    db = get_db()
    return db.run(sql)
