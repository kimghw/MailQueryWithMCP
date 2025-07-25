"""Template management module for IACSGRAPH"""

from pathlib import Path

TEMPLATES_ROOT = Path(__file__).parent
DATA_DIR = TEMPLATES_ROOT / "data"
UNIFIED_TEMPLATES_PATH = DATA_DIR / "unified" / "query_templates_unified.json"

__version__ = "1.0.0"
__all__ = ["TEMPLATES_ROOT", "DATA_DIR", "UNIFIED_TEMPLATES_PATH"]