"""
Data Normalizers for SAP O2C Pipeline.

Applies type casting, null handling, date parsing, nested-field flattening,
and deduplication to raw DataFrames based on entity schema definitions.
"""

import logging

import pandas as pd

from config import ENTITY_SCHEMAS

logger = logging.getLogger(__name__)


def _flatten_nested_time_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Flatten a nested time-object column like:
        {"hours": 6, "minutes": 49, "seconds": 13}
    into three columns + a combined HH:MM:SS string column.
    """
    if col not in df.columns:
        return df

    # Extract the nested dict; handle None/NaN rows
    time_data = df[col].apply(
        lambda x: x if isinstance(x, dict) else {"hours": None, "minutes": None, "seconds": None}
    )

    df[f"{col}_hours"] = time_data.apply(lambda x: x.get("hours"))
    df[f"{col}_minutes"] = time_data.apply(lambda x: x.get("minutes"))
    df[f"{col}_seconds"] = time_data.apply(lambda x: x.get("seconds"))

    # Build HH:MM:SS string (NaN if any component is missing)
    def _format_time(row_prefix):
        h = row_prefix.get("hours")
        m = row_prefix.get("minutes")
        s = row_prefix.get("seconds")
        if h is None or m is None or s is None:
            return None
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

    df[f"{col}_formatted"] = time_data.apply(_format_time)

    # Drop the original nested column
    df = df.drop(columns=[col])
    logger.info(f"    Flattened nested column: {col} → {col}_hours/minutes/seconds/formatted")
    return df


def _parse_datetime_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Parse ISO-8601 datetime strings to pandas datetime64."""
    for col in cols:
        if col not in df.columns:
            continue
        # Replace empty strings with None before parsing
        df[col] = df[col].replace("", None)
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        parsed_count = df[col].notna().sum()
        logger.info(f"    Parsed datetime: {col} ({parsed_count}/{len(df)} non-null)")
    return df


def _cast_numeric_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Cast string-encoded numeric columns to float64."""
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df[col].replace("", None)
        df[col] = pd.to_numeric(df[col], errors="coerce")
        logger.info(f"    Cast numeric: {col} (dtype={df[col].dtype})")
    return df


def _cast_bool_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Ensure boolean columns are proper pandas booleans."""
    for col in cols:
        if col not in df.columns:
            continue
        # Handle various representations: True/False, "true"/"false", 1/0, ""
        df[col] = df[col].replace("", None)
        df[col] = df[col].map(
            {True: True, False: False, "true": True, "false": False, 1: True, 0: False}
        ).astype("boolean")  # nullable boolean dtype
        logger.info(f"    Cast boolean: {col}")
    return df


def _clean_empty_strings(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Replace empty strings with NaN for columns that are NOT purely text.
    For text columns (str_cols), keep empty strings as-is unless they look
    like they should be null.
    """
    typed_cols = set(
        schema.get("datetime_cols", [])
        + schema.get("numeric_cols", [])
        + schema.get("bool_cols", [])
        + schema.get("nested_cols", [])
    )
    for col in df.columns:
        if col in typed_cols:
            continue  # Already handled by specific casters
        # For string columns keep empty strings, but replace whitespace-only with NaN
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda x: None if isinstance(x, str) and x.strip() == "" else (x.strip() if isinstance(x, str) else x)
            )
    return df


def _deduplicate(df: pd.DataFrame, primary_keys: list[str]) -> pd.DataFrame:
    """Drop fully duplicate rows, then warn about duplicate primary keys."""
    before = len(df)
    df = df.drop_duplicates()
    exact_dupes = before - len(df)
    if exact_dupes > 0:
        logger.warning(f"    Removed {exact_dupes} exact duplicate rows")

    if primary_keys:
        pk_cols = [c for c in primary_keys if c in df.columns]
        if pk_cols:
            pk_dupes = df.duplicated(subset=pk_cols, keep=False).sum()
            if pk_dupes > 0:
                logger.warning(
                    f"    Found {pk_dupes} rows with duplicate primary keys {pk_cols} "
                    f"(keeping first occurrence)"
                )
                df = df.drop_duplicates(subset=pk_cols, keep="first")
    return df


def normalize_entity(df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
    """
    Apply all normalization steps to a raw entity DataFrame.

    Steps:
        1. Flatten nested objects (time dicts)
        2. Parse datetime columns
        3. Cast numeric columns
        4. Cast boolean columns
        5. Clean empty strings → NaN for non-text fields
        6. Deduplicate
    """
    if df.empty:
        return df

    schema = ENTITY_SCHEMAS.get(entity_name, {})
    logger.info(f"  Normalizing [{entity_name}] ({len(df)} rows, {len(df.columns)} cols)...")

    # 1. Flatten nested columns
    for nested_col in schema.get("nested_cols", []):
        df = _flatten_nested_time_col(df, nested_col)

    # 2. Parse datetimes
    df = _parse_datetime_cols(df, schema.get("datetime_cols", []))

    # 3. Cast numerics
    df = _cast_numeric_cols(df, schema.get("numeric_cols", []))

    # 4. Cast booleans
    df = _cast_bool_cols(df, schema.get("bool_cols", []))

    # 5. Clean empty strings
    df = _clean_empty_strings(df, schema)

    # 6. Deduplicate
    df = _deduplicate(df, schema.get("primary_keys", []))

    logger.info(f"  Normalized [{entity_name}]: {len(df)} rows, {len(df.columns)} cols")
    return df


def normalize_all(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Normalize all entity DataFrames in the dict."""
    normalized = {}
    for name, df in data.items():
        normalized[name] = normalize_entity(df, name)
    return normalized
