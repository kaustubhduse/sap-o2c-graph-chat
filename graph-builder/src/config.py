"""
Configuration for the graph builder.
"""
from pathlib import Path

# Base directory for the graph-builder application
BASE_DIR = Path(__file__).resolve().parent.parent

# Read from the data-processing pipeline output
ENTITIES_DIR = BASE_DIR.parent / "data-processing" / "output" / "entities"

# Write graph output to graph-builder/output
GRAPH_DIR = BASE_DIR / "output"
