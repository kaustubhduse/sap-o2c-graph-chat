"""
Database connection layer using LangChain's SQLDatabase and PyMySQL.
Connects to the MySQL database containing the SAP O2C tables.

Prefer MYSQL_URL (or DATABASE_URL), e.g. Railway:
  mysql://user:pass@host:port/dbname
Scheme mysql:// is normalized to mysql+pymysql:// for SQLAlchemy.
"""
import os
import logging
from urllib.parse import urlparse, urlunparse, unquote, parse_qsl, urlencode

from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase

load_dotenv()
logger = logging.getLogger(__name__)

import urllib.parse

_db_instance = None


def _normalize_mysql_scheme(url: str) -> str:
    u = url.strip()
    if u.startswith("mysql://") and not u.startswith("mysql+pymysql"):
        u = "mysql+pymysql://" + u[len("mysql://") :]
    # PyMySQL does not accept options like `ssl-mode=REQUIRED` from some providers.
    # Drop dashed query keys to avoid TypeError: unexpected keyword argument.
    p = urlparse(u)
    if p.query:
        q = parse_qsl(p.query, keep_blank_values=True)
        filtered = [(k, v) for (k, v) in q if "-" not in k]
        if len(filtered) != len(q):
            u = urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(filtered), p.fragment))
    return u


def _mysql_url_from_env() -> str | None:
    raw = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")
    if not raw or not str(raw).strip():
        return None
    return _normalize_mysql_scheme(str(raw).strip())


def _parse_url_to_legacy_vars(url: str) -> tuple[str, str, str, str, str]:
    """Return DB_USER, DB_PASSWORD (quoted for URI), DB_HOST, DB_PORT, DB_NAME."""
    p = urlparse(url)
    user = unquote(p.username or "root")
    raw_pw = unquote(p.password) if p.password else ""
    host = p.hostname or "127.0.0.1"
    port = str(p.port or 3306)
    name = (p.path or "/").strip("/") or "mysql"
    quoted_pw = urllib.parse.quote_plus(raw_pw)
    return user, quoted_pw, host, port, name


# Resolved config: MYSQL_URL wins over DB_* pieces
_mysql_url = _mysql_url_from_env()
if _mysql_url:
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = _parse_url_to_legacy_vars(_mysql_url)
else:
    DB_USER = os.getenv("DB_USER", "root")
    raw_password = os.getenv("DB_PASSWORD", "")
    DB_PASSWORD = urllib.parse.quote_plus(raw_password)
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "db-1")


def get_sqlalchemy_uri() -> str:
    """Full SQLAlchemy URI including database name."""
    if _mysql_url:
        return _mysql_url
    return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_server_sqlalchemy_uri() -> str:
    """Same server, no database in path (for CREATE DATABASE, etc.)."""
    if _mysql_url:
        p = urlparse(_mysql_url)
        return urlunparse((p.scheme, p.netloc, "", "", "", ""))
    return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"


def get_db() -> SQLDatabase:
    """
    Return a singleton LangChain SQLDatabase connected to MySQL.
    Uses pymysql driver.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    uri = get_sqlalchemy_uri()
    logger.info(f"Connecting to MySQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    _db_instance = SQLDatabase.from_uri(
        uri,
        sample_rows_in_table_info=3,
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
