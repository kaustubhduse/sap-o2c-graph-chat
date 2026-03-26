"""
SAP O2C Graph Builder -- Main Entry Point.

Usage:
    python main.py          # Build graph from preprocessed entity CSVs
"""

import sys
import logging
import time
from pathlib import Path

# Add the project root to sys.path so 'src' can be imported 
sys.path.append(str(Path(__file__).resolve().parent))

from src.builder import build_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    start_time = time.time()
    print("\n" + "#" * 60)
    print("  SAP O2C Graph Construction")
    print("#" * 60 + "\n")

    nodes, edges = build_graph()

    elapsed = time.time() - start_time
    print("\n" + "#" * 60)
    print(f"  Graph built in {elapsed:.1f}s")
    print(f"  Nodes: {len(nodes):,}  |  Edges: {len(edges):,}")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
