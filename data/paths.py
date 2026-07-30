from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parent.parent
DATABASE_ROOT = DASHBOARD_ROOT.parent / "naot_navon_database"

APARTMENTS_JSON = DATABASE_ROOT / "apartments_database.json"
QUALITY_JSON = DATABASE_ROOT / "apartments_quality_analysis.json"
VALUE_JSON = DATABASE_ROOT / "apartments_value_analysis.json"
PROJECT_JSON = DATABASE_ROOT / "03_planning" / "project.json"
