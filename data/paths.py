from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parent.parent

_LOCAL_DB = DASHBOARD_ROOT / "naot_navon_database"
_SIBLING_DB = DASHBOARD_ROOT.parent / "naot_navon_database"
DATABASE_ROOT = _LOCAL_DB if _LOCAL_DB.exists() else _SIBLING_DB

APARTMENTS_JSON = DATABASE_ROOT / "apartments_database.json"
QUALITY_JSON = DATABASE_ROOT / "apartments_quality_analysis.json"
VALUE_JSON = DATABASE_ROOT / "apartments_value_analysis.json"
ARCHITECTURE_JSON = DATABASE_ROOT / "apartments_architecture_analysis.json"
PROJECT_JSON = DATABASE_ROOT / "03_planning" / "project.json"
