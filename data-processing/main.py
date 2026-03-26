"""
SAP O2C Data Preprocessing Pipeline — Main Orchestrator.

Usage:
    python main.py                  # Run full pipeline
    python main.py --skip-joins     # Normalize only, skip joined datasets
    python main.py --entities-only sales_order_headers billing_document_headers
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

from config import ENTITY_NAMES, ENTITY_SCHEMAS, ENTITIES_OUTPUT_DIR, JOINED_OUTPUT_DIR
from loaders import load_all_entities, load_entity
from normalizers import normalize_all, normalize_entity
from joiners import build_all_joins

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_dataframe(df: pd.DataFrame, filepath: Path, label: str) -> None:
    """Save a DataFrame to CSV with logging."""
    if df.empty:
        logger.warning(f"  Skipping empty DataFrame: {label}")
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    size_kb = filepath.stat().st_size / 1024
    logger.info(f"  Saved {label}: {len(df):,} rows → {filepath.name} ({size_kb:.1f} KB)")


def print_summary_table(data: dict[str, pd.DataFrame], title: str) -> None:
    """Print a formatted summary table of all DataFrames."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")
    print(f"  {'Entity':<50} {'Rows':>8} {'Cols':>6} {'Nulls%':>8}")
    print(f"  {'-' * 50} {'-' * 8} {'-' * 6} {'-' * 8}")

    total_rows = 0
    for name, df in data.items():
        if df.empty:
            print(f"  {name:<50} {'(empty)':>8}")
            continue
        rows = len(df)
        cols = len(df.columns)
        null_pct = (df.isnull().sum().sum() / (rows * cols) * 100) if rows * cols > 0 else 0
        total_rows += rows
        print(f"  {name:<50} {rows:>8,} {cols:>6} {null_pct:>7.1f}%")

    print(f"  {'-' * 50} {'-' * 8}")
    print(f"  {'TOTAL':<50} {total_rows:>8,}")
    print(f"{'=' * 80}\n")


def print_dtype_report(data: dict[str, pd.DataFrame]) -> None:
    """Print a summary of data types per entity to verify normalization."""
    print(f"\n{'=' * 80}")
    print("  Data Type Summary (after normalization)")
    print(f"{'=' * 80}")

    for name, df in data.items():
        if df.empty:
            continue
        dtype_counts = df.dtypes.value_counts()
        dtype_str = ", ".join(f"{dtype}: {count}" for dtype, count in dtype_counts.items())
        print(f"  {name:<45} | {dtype_str}")

    print(f"{'=' * 80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="SAP O2C Data Preprocessing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Full pipeline (normalize + join)
  python main.py --skip-joins       Normalize entities only
  python main.py --entities-only sales_order_headers products
        """,
    )
    parser.add_argument(
        "--skip-joins",
        action="store_true",
        help="Skip building joined datasets, only output normalized entities",
    )
    parser.add_argument(
        "--entities-only",
        nargs="*",
        metavar="ENTITY",
        help="Process only specific entities (space-separated names)",
    )
    args = parser.parse_args()

    start_time = time.time()
    print("\n" + "#" * 80)
    print("  SAP O2C Data Preprocessing Pipeline")
    print("#" * 80 + "\n")

    # ── Step 1: Load ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1/4: Loading JSONL data...")
    logger.info("=" * 60)

    if args.entities_only:
        # Validate entity names
        invalid = [e for e in args.entities_only if e not in ENTITY_NAMES]
        if invalid:
            logger.error(f"Unknown entities: {invalid}")
            logger.error(f"Available: {ENTITY_NAMES}")
            sys.exit(1)
        raw_data = {}
        for name in args.entities_only:
            logger.info(f"Loading [{name}]...")
            raw_data[name] = load_entity(name)
    else:
        raw_data = load_all_entities()

    print_summary_table(raw_data, "Raw Data (before normalization)")

    # ── Step 2: Normalize ─────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 2/4: Normalizing data...")
    logger.info("=" * 60)

    normalized_data = normalize_all(raw_data)

    print_summary_table(normalized_data, "Normalized Data")
    print_dtype_report(normalized_data)

    # ── Step 3: Save normalized entities ──────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 3/4: Saving normalized entity CSVs...")
    logger.info("=" * 60)

    for name, df in normalized_data.items():
        filepath = ENTITIES_OUTPUT_DIR / f"{name}.csv"
        save_dataframe(df, filepath, name)

    # ── Step 4: Join & save ───────────────────────────────────────────────
    if not args.skip_joins and not args.entities_only:
        logger.info("=" * 60)
        logger.info("STEP 4/4: Building joined datasets...")
        logger.info("=" * 60)

        joined_data = build_all_joins(normalized_data)

        print_summary_table(joined_data, "Joined Datasets")

        for name, df in joined_data.items():
            filepath = JOINED_OUTPUT_DIR / f"{name}.csv"
            save_dataframe(df, filepath, name)
    else:
        logger.info("STEP 4/4: Skipped (--skip-joins or --entities-only)")

    # ── Done ──────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "#" * 80)
    print(f"  Pipeline completed in {elapsed:.1f}s")
    print(f"  Output directory: {ENTITIES_OUTPUT_DIR.parent.resolve()}")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    main()
