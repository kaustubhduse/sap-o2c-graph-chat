"""
Data Loaders for SAP O2C Pipeline.

Reads JSONL part-files from each entity subdirectory and merges them
into a single pandas DataFrame per entity.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from config import INPUT_DIR, ENTITY_NAMES

logger = logging.getLogger(__name__)


def load_jsonl_file(filepath: Path) -> list[dict]:
    """Parse a single JSONL file into a list of dicts."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"  Skipping malformed JSON at {filepath.name}:{line_num}: {e}")
    return records


def load_entity(entity_name: str) -> pd.DataFrame:
    """
    Load all JSONL part-files for an entity into a single DataFrame.

    Args:
        entity_name: Subdirectory name under INPUT_DIR (e.g., 'sales_order_headers')

    Returns:
        Concatenated DataFrame of all records, or empty DataFrame if no files found.
    """
    entity_dir = INPUT_DIR / entity_name

    if not entity_dir.exists():
        logger.error(f"  Directory not found: {entity_dir}")
        return pd.DataFrame()

    jsonl_files = sorted(entity_dir.glob("*.jsonl"))

    if not jsonl_files:
        logger.warning(f"  No JSONL files found in {entity_dir}")
        return pd.DataFrame()

    all_records = []
    for fpath in jsonl_files:
        records = load_jsonl_file(fpath)
        logger.info(f"  Loaded {len(records):>6,} rows from {fpath.name}")
        all_records.extend(records)

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    logger.info(f"  Total: {len(df):>6,} rows, {len(df.columns)} columns")
    return df


def load_all_entities() -> dict[str, pd.DataFrame]:
    """
    Load all 19 entities into a dict of DataFrames.

    Returns:
        Dict mapping entity_name → DataFrame
    """
    data = {}
    for name in ENTITY_NAMES:
        logger.info(f"Loading [{name}]...")
        data[name] = load_entity(name)
    return data
