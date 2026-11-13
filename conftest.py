"""
MAITRI 2.0 — pytest conftest.py (root)
Adds project root to sys.path so backend.* and modules.* resolve correctly.
"""
import sys
from pathlib import Path

# Project root (contains backend/, modules/, tests/)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
