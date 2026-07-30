"""Load and merge apartment data from naot_navon_database."""
import json
import pandas as pd

from data.paths import APARTMENTS_JSON, QUALITY_JSON, VALUE_JSON, PROJECT_JSON
from utils.premium_exit import apply_premium_exit_scores


def _read_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_price(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("₪", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_project() -> dict:
    data = _read_json(PROJECT_JSON)
    return data or {}


def load_apartments() -> pd.DataFrame:
    """Primary source: apartments_database.json, enriched with quality/value analysis."""
    base = _read_json(APARTMENTS_JSON)
    if not base:
        raise FileNotFoundError(f"לא נמצא קובץ נתונים: {APARTMENTS_JSON}")

    df = pd.DataFrame(base)

    # Normalize numeric fields from primary source
    for col in ("area_sqm", "balcony_garden_sqm", "storage_sqm"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["rooms_num"] = pd.to_numeric(df["rooms"].astype(str).str.replace(",", "."), errors="coerce")
    df["price_total"] = df["final_price"].apply(_parse_price)

    # Enrich from analysis files (keyed by id)
    quality = _read_json(QUALITY_JSON)
    if quality:
        qdf = pd.DataFrame(quality)
        q_cols = [c for c in [
            "id", "quality_score", "score_view", "score_location", "score_planning",
            "score_rarity", "view_classification", "notes",
        ] if c in qdf.columns]
        qdf = qdf[q_cols].rename(columns={"notes": "notes_quality"})
        df = df.merge(qdf, on="id", how="left")

    value = _read_json(VALUE_JSON)
    if value:
        vdf = pd.DataFrame(value)
        v_cols = [c for c in [
            "id", "price_per_sqm_built", "price_per_sqm_incl_balcony",
            "deviation_from_project_pct", "price_position", "price_score",
            "liquidity_score", "pricing_risk", "value_score", "value_rank",
            "quality_per_million",
        ] if c in vdf.columns]
        vdf = vdf[v_cols]
        df = df.merge(vdf, on="id", how="left")

    # Derived columns
    if "price_per_sqm_built" not in df.columns or df["price_per_sqm_built"].isna().all():
        df["price_per_sqm_built"] = df.apply(
            lambda r: r["price_total"] / r["area_sqm"]
            if pd.notna(r.get("price_total")) and pd.notna(r.get("area_sqm")) and r["area_sqm"] > 0
            else None,
            axis=1,
        )

    df["building_num"] = pd.to_numeric(df["building"], errors="coerce")
    df["apartment_num"] = pd.to_numeric(df["apartment_number"], errors="coerce")
    df["label"] = df.apply(lambda r: f"מבנה {r['building']} / דירה {r['apartment_number']}", axis=1)
    df["has_price"] = df["price_total"].notna()

    df = apply_premium_exit_scores(df)

    return df
