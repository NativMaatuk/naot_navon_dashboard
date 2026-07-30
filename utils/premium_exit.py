"""Premium Exit Score — potential desirability in free market in 5-10 years."""
from __future__ import annotations

import pandas as pd

from utils.floor import floor_numeric

TOWERS = {7, 14}
TOWER_MAX = 21
LOW_RISE_MAX = {1: 6, 2: 7, 3: 7, 4: 6, 5: 7, 6: 7, 8: 7, 9: 6, 10: 7, 11: 7, 12: 6, 13: 7}

WEIGHTS = {
    "view": 0.30,
    "floor": 0.20,
    "rarity": 0.20,
    "planning": 0.15,
    "outdoor": 0.10,
    "price": 0.05,
}


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def score_view(row: pd.Series) -> float:
    base = float(row.get("score_view") or 50)
    view_cls = str(row.get("view_classification") or "")
    if "פנורמי" in view_cls or "ים" in view_cls:
        base = max(base, 85)
    if "רב-כיווני" in view_cls or "4 כיווני" in str(row.get("directions", "")):
        base += 5
    directions = str(row.get("directions") or "")
    if "מערב" in directions:
        base += 8
    if directions.count("/") >= 2 or directions.count(" ") >= 3:
        base += 4
    return round(_clamp(base), 1)


def score_floor(row: pd.Series) -> float:
    building = int(row.get("building_num") or row.get("building") or 0)
    floor = row.get("floor")
    fn = floor_numeric(floor)
    balcony = float(row.get("balcony_garden_sqm") or 0)
    max_f = TOWER_MAX if building in TOWERS else LOW_RISE_MAX.get(building, 7)

    if building in TOWERS:
        if fn >= 19:
            return 98.0
        if fn >= 15:
            return 88.0 + (fn - 15) * 2
        if fn >= 8:
            return 65.0 + (fn - 8) * 3
        if fn >= 1:
            return 50.0 + fn * 2
        return 42.0

    if fn == 0 and balcony >= 120:
        return 90.0
    if fn == 0 and balcony >= 80:
        return 78.0
    if fn == max_f:
        return 84.0
    if fn >= 5:
        return 58.0 + fn * 3
    if fn >= 1:
        return 48.0 + fn * 2
    if fn == -1:
        return 55.0
    return 45.0


def score_rarity(row: pd.Series) -> float:
    return round(_clamp(float(row.get("score_rarity") or 50)), 1)


def score_planning(row: pd.Series) -> float:
    return round(_clamp(float(row.get("score_planning") or 50)), 1)


def score_outdoor(row: pd.Series, balcony_p90: float, balcony_p50: float) -> float:
    balcony = float(row.get("balcony_garden_sqm") or 0)
    if balcony_p90 <= 0:
        return 50.0
    if balcony >= balcony_p90:
        return 95.0
    if balcony >= balcony_p50:
        ratio = (balcony - balcony_p50) / max(balcony_p90 - balcony_p50, 1)
        return round(60 + ratio * 30, 1)
    ratio = balcony / max(balcony_p50, 1)
    return round(35 + ratio * 25, 1)


def score_price_relative(row: pd.Series) -> float:
    """Moderate 5% component — fair pricing, not automatic preference for low price."""
    if not row.get("has_price"):
        return 55.0
    dev = row.get("deviation_from_project_pct")
    if pd.isna(dev):
        return 55.0
    dev = float(dev)
    # Peak around market average; penalize extreme cheap OR expensive equally mildly
    distance = abs(dev)
    if distance <= 3:
        return 72.0
    if distance <= 6:
        return 65.0
    if distance <= 10:
        return 58.0
    return 50.0


def compute_subscores(row: pd.Series, balcony_p90: float, balcony_p50: float) -> dict[str, float]:
    return {
        "premium_view": score_view(row),
        "premium_floor": score_floor(row),
        "premium_rarity": score_rarity(row),
        "premium_planning": score_planning(row),
        "premium_outdoor": score_outdoor(row, balcony_p90, balcony_p50),
        "premium_price": score_price_relative(row),
    }


def compute_total(sub: dict[str, float]) -> float:
    return round(
        sub["premium_view"] * WEIGHTS["view"]
        + sub["premium_floor"] * WEIGHTS["floor"]
        + sub["premium_rarity"] * WEIGHTS["rarity"]
        + sub["premium_planning"] * WEIGHTS["planning"]
        + sub["premium_outdoor"] * WEIGHTS["outdoor"]
        + sub["premium_price"] * WEIGHTS["price"],
        1,
    )


def explain_premium_exit(row: pd.Series, sub: dict[str, float], top_n_dims: int = 3) -> list[str]:
    """Generate Hebrew textual reasons for high ranking."""
    dim_labels = {
        "premium_view": ("נוף ופתיחות", [
            (85, "דורגה גבוה בגלל נוף ים / פנורמי נדיר"),
            (75, "דורגה גבוה בגלל נוף פתוח וכיווני אוויר מרובים"),
            (65, "דורגה גבוה בגלל פוטנציאל נוף טוב"),
        ]),
        "premium_floor": ("קומה", [
            (90, "דורגה גבוה בגלל קומת פנטהאוז / גג יוקרתית"),
            (80, "דורגה גבוה בגלל קומה גבוהה במגדל"),
            (75, "דורגה גבוה בגלל דירת גן עם שטח חוץ פרטי גדול"),
            (65, "דורגה גבוה בגלל מיקום קומתי מועדף"),
        ]),
        "premium_rarity": ("נדירות", [
            (90, "דורגה גבוה בגלל נדירות יוצאת דופן בפרויקט"),
            (75, "דורגה גבוה בגלל טיפוס דירה נדיר"),
            (65, "דורגה גבוה בגלל מוגבלות יחידות מסוג זה"),
        ]),
        "premium_planning": ("תכנון", [
            (80, "דורגה גבוה בגלל תכנון פונקציונלי ושטחים מאוזנים"),
            (70, "דורגה גבוה בגלל יעילות תכנון טובה"),
        ]),
        "premium_outdoor": ("מרפסת וחוץ", [
            (90, "דורגה גבוה בגלל מרפסת / גינה גדולה במיוחד"),
            (75, "דורגה גבוה בגלל שטח חוץ משמעותי"),
        ]),
        "premium_price": ("מחיר", [
            (70, "דורגה גבוה בגלל מחיר מאוזן ביחס לפרויקט"),
            (65, "דורגה גבוה בגלל תמחור הוגן ביחס לממוצע"),
        ]),
    }

    weight_map = {
        "premium_view": WEIGHTS["view"],
        "premium_floor": WEIGHTS["floor"],
        "premium_rarity": WEIGHTS["rarity"],
        "premium_planning": WEIGHTS["planning"],
        "premium_outdoor": WEIGHTS["outdoor"],
        "premium_price": WEIGHTS["price"],
    }
    ranked_dims = sorted(
        [(k, sub[k]) for k in dim_labels],
        key=lambda x: x[1] * weight_map[x[0]],
        reverse=True,
    )

    reasons: list[str] = []
    used_texts: set[str] = set()

    for dim_key, score in ranked_dims:
        if len(reasons) >= top_n_dims:
            break
        if score < 60:
            continue
        _, thresholds = dim_labels[dim_key]
        for threshold, text in thresholds:
            if score >= threshold and text not in used_texts:
                reasons.append(text)
                used_texts.add(text)
                break

    if len(reasons) >= 2:
        combo = "דורגה גבוה בגלל שילוב של " + " ו".join(
            [r.replace("דורגה גבוה בגלל ", "") for r in reasons[:2]]
        )
        if combo not in used_texts:
            reasons.append(combo)

    if not reasons:
        if sub.get("premium_view", 0) >= 50:
            reasons.append("דורגה בינונית-גבוהה — פרופיל מאוזן ללא יתרון דומיננטי אחד")
        else:
            reasons.append("דורגה לפי פרופיל כללי בפרויקט")

    return reasons


def apply_premium_exit_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    balconies = out["balcony_garden_sqm"].dropna()
    p90 = float(balconies.quantile(0.9)) if len(balconies) else 100
    p50 = float(balconies.quantile(0.5)) if len(balconies) else 50

    subscores_list = []
    totals = []
    reasons_list = []

    for _, row in out.iterrows():
        sub = compute_subscores(row, p90, p50)
        subscores_list.append(sub)
        totals.append(compute_total(sub))
        reasons_list.append(explain_premium_exit(row, sub))

    sub_df = pd.DataFrame(subscores_list)
    out = pd.concat([out.reset_index(drop=True), sub_df], axis=1)
    out["premium_exit_score"] = totals
    out["premium_exit_reasons"] = [r for r in reasons_list]
    out["premium_exit_reasons_text"] = [" | ".join(r) for r in reasons_list]

    ranked = out["premium_exit_score"].rank(ascending=False, method="min").astype("Int64")
    out["premium_exit_rank"] = ranked

    return out
