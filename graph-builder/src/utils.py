"""
Utility functions for data loading and graph construction.
"""
import logging
import pandas as pd
from src.config import ENTITIES_DIR

logger = logging.getLogger(__name__)

def safe_val(val):
    """Return stripped string or None if NaN / empty."""
    if pd.isna(val) or str(val).strip() == "":
        return None
    return str(val).strip()


def extract_props(row, cols):
    """Extract non-null properties from a DataFrame row."""
    out = {}
    for c in cols:
        if c in row.index:
            v = safe_val(row[c])
            if v is not None:
                out[c] = v
    return out


def load_entity(name):
    """Load an entity CSV as strings; return empty DF if missing."""
    p = ENTITIES_DIR / f"{name}.csv"
    if not p.exists():
        logger.warning(f"Missing: {p}")
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str).fillna("")


def add_node(nodes_list, id_set, node_id, node_type, label, properties):
    """Add a node to the graph if it doesn't already exist."""
    if node_id in id_set:
        return
    id_set.add(node_id)
    nodes_list.append({
        "id": node_id, 
        "type": node_type, 
        "label": label,
        "properties": properties
    })


def add_edge(edges_list, eid_set, source, target, edge_type, props=None):
    """Add an edge to the graph if it doesn't already exist."""
    if not source or not target:
        return
    key = (source, target, edge_type)
    if key in eid_set:
        return
    eid_set.add(key)
    edges_list.append({
        "source": source, 
        "target": target, 
        "type": edge_type,
        "properties": props or {}
    })
