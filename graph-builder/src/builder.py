"""
Main orchestrator for graph construction.
"""
import json
import logging
from collections import Counter

from src.config import GRAPH_DIR
from src.nodes import (
    build_customer_nodes, build_sales_order_nodes, build_product_nodes,
    build_delivery_nodes, build_billing_nodes, build_journal_nodes,
    build_payment_nodes, build_plant_nodes
)
from src.edges import build_all_edges

logger = logging.getLogger(__name__)


def build_graph():
    """Build the complete property graph and save to JSON."""
    nodes, edges = [], []
    nids, eids = set(), set()

    logger.info("--- Building Nodes ---")
    build_customer_nodes(nodes, nids)
    build_sales_order_nodes(nodes, nids)
    build_product_nodes(nodes, nids)
    build_delivery_nodes(nodes, nids)
    build_billing_nodes(nodes, nids)
    build_journal_nodes(nodes, nids)
    build_payment_nodes(nodes, nids)
    build_plant_nodes(nodes, nids)
    logger.info(f"Total nodes: {len(nodes)}")

    logger.info("--- Building Edges ---")
    build_all_edges(edges, eids, nids)
    logger.info(f"Total edges: {len(edges)}")

    # -- Referential integrity check ----------------------------------------
    dangling_src = [e for e in edges if e["source"] not in nids]
    dangling_tgt = [e for e in edges if e["target"] not in nids]
    if dangling_src or dangling_tgt:
        logger.warning(f"Dangling edges: {len(dangling_src)} bad sources, "
                       f"{len(dangling_tgt)} bad targets")
        for e in dangling_src[:5]:
            logger.warning(f"  bad source: {e['source']} -> {e['target']} ({e['type']})")
        for e in dangling_tgt[:5]:
            logger.warning(f"  bad target: {e['source']} -> {e['target']} ({e['type']})")
    else:
        logger.info("Referential integrity OK -- all edge endpoints exist as nodes")

    # -- Save ---------------------------------------------------------------
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_DIR / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    with open(GRAPH_DIR / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2, ensure_ascii=False)

    # -- Summary ------------------------------------------------------------
    nc = Counter(n["type"] for n in nodes)
    ec = Counter(e["type"] for e in edges)
    logger.info("--- Node Summary ---")
    for t, c in sorted(nc.items()):
        logger.info(f"  {t:20s} {c:>6,}")
    logger.info("--- Edge Summary ---")
    for t, c in sorted(ec.items()):
        logger.info(f"  {t:25s} {c:>6,}")
    logger.info(f"Saved to {GRAPH_DIR}")

    return nodes, edges
