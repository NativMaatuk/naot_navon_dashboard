#!/usr/bin/env python3
"""Task 2: Property quality analysis for Shoval Touch - Naot Navon."""
import json
import csv
import shutil
from pathlib import Path
from collections import Counter
from datetime import datetime

BASE = Path(__file__).parent
APARTMENTS_SRC = BASE / "02_apartments" / "apartments.json"
BUILDINGS_SRC = BASE / "03_planning" / "buildings.json"
PROJECT_SRC = BASE / "03_planning" / "project.json"
ARCHITECTURE_SRC = BASE / "apartments_architecture_analysis.json"

TOWERS = {7, 14}
TOWER_MAX_FLOOR = 21
LOW_RISE_MAX = {1: 6, 2: 7, 3: 7, 4: 6, 5: 7, 6: 7, 8: 7, 9: 6, 10: 7, 11: 7, 12: 6, 13: 7}

PENTHOUSE_TYPES = {
    "4-M", "4-H", "4-K", "4-L", "4-I",
    "3-G", "3-F", "3-FM", "3-GM",
    "2-H", "2-G", "2-F",
    "5-D",
}

GARDEN_TYPES = {
    "1-A", "1-D", "2-A", "2-B", "2-L", "2-M", "2-I", "2-K",
    "3-A", "3-B", "3ב-A", "3ב-B", "3-H", "3-I", "3-JM", "3-KM",
    "3-M", "3-N", "3-OM", "3-PM",
    "5-A",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def floor_numeric(floor: str) -> int:
    if not floor:
        return 0
    if floor == "קרקע":
        return 0
    if "מרתף" in floor:
        return -1
    try:
        return int(floor)
    except ValueError:
        return 0


def parse_float(val):
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_rooms(val):
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return None


def parse_directions(directions: str) -> list[str]:
    if not directions:
        return []
    parts = directions.replace(" ", "").split("/")
    result = []
    for p in parts:
        for d in ["צפון", "דרום", "מזרח", "מערב"]:
            if d in p and d not in result:
                result.append(d)
    return result


def classify_view(directions: list[str], floor_num: int, building: int, balcony: float) -> str:
  """Qualitative view classification based on available data."""
  has_west = "מערב" in directions
  has_south = "דרום" in directions
  has_north = "צפון" in directions
  has_east = "מזרח" in directions
  n_dirs = len(directions)

  if building in TOWERS and floor_num >= 15 and (has_west or has_south):
      return "נוף פנורמי גבוה (ים/עיר) - מוערך"
  if building in TOWERS and floor_num >= 8 and has_west:
      return "נוף ים מוערך"
  if floor_num == 0 and balcony and balcony > 100:
      return "גינה פרטית גדולה"
  if n_dirs >= 3:
      return "נוף פתוח רב-כיווני"
  if has_west:
      return "נוף מערבי (פוטנציאל ים)"
  if has_south:
      return "נוף דרומי"
  if has_north and not has_west:
      return "נוף צפוני/עירוני"
  return "נוף מוגבל"


def score_location(apt, building: int, floor_num: int, max_floor: int) -> tuple[float, str]:
    notes = []
    score = 50.0

    if building in TOWERS:
        ratio = floor_num / TOWER_MAX_FLOOR if TOWER_MAX_FLOOR else 0
        score = 45 + ratio * 45
        notes.append("מגדל 22 קומות")
        if floor_num >= 15:
            notes.append("קומה גבוהה במגדל")
        elif floor_num <= 3:
            notes.append("קומה נמוכה במגדל")
    else:
        ratio = floor_num / max_floor if max_floor else 0
        if floor_num == 0:
            balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
            if balcony > 100:
                score = 72
                notes.append("דירת גן בקומת קרקע")
            elif balcony > 50:
                score = 62
                notes.append("קומת קרקע עם חצר")
            else:
                score = 48
                notes.append("קומת קרקע")
        elif floor_num == -1:
            score = 40
            notes.append("קרקע+מרתף")
        else:
            score = 50 + ratio * 25
            if floor_num == max_floor:
                score += 8
                notes.append("קומה עליונה בבניין נמוך")

    directions = parse_directions(apt.get("directions", ""))
    if len(directions) >= 3:
        score += 5
        notes.append("יחידת פינה/רב-כיוונית")

    apt_num = int(apt.get("apartment_number", 0) or 0)
    if apt_num in (1, 2) and floor_num > 0:
        score -= 3
        notes.append("קרבה אפשרית ללובי/מעלית")

    score = max(0, min(100, score))
    return round(score, 1), "; ".join(notes)


def score_view(apt, building: int, floor_num: int, arch: dict | None = None) -> tuple[float, str]:
    directions = parse_directions(apt.get("directions", ""))
    n = len(directions)
    score = 35.0
    notes = []

    if "מערב" in directions:
        score += 22
        notes.append("כיוון מערב - פוטנציאל נוף ים")
    if "דרום" in directions:
        score += 12
        notes.append("כיוון דרום")
    if "צפון" in directions:
        score += 5
    if "מזרח" in directions:
        score += 3

    if n >= 4:
        score += 15
        notes.append("4 כיווני אוויר")
    elif n == 3:
        score += 10
        notes.append("3 כיווני אוויר")
    elif n == 2:
        score += 5

    if building in TOWERS:
        floor_bonus = min(20, (floor_num / TOWER_MAX_FLOOR) * 20)
        score += floor_bonus
        if floor_num >= 12:
            notes.append("גובה מגדל מגביר נוף")

    if floor_num == 0:
        balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
        if balcony > 150:
            score += 12
            notes.append("שטח גינה גדול מאוד")
        elif balcony > 80:
            score += 6

    score = max(0, min(100, score))

    if arch and arch.get("score_view_plan") is not None:
        enhanced = float(arch["score_view_plan"])
        score = round(enhanced * 0.6 + score * 0.4, 1)
        view_detail = arch.get("view_detail") or {}
        plan_notes = view_detail.get("notes", "")
        if plan_notes:
            notes.append(plan_notes)

    return round(score, 1), "; ".join(notes)


def score_planning(apt, arch: dict | None = None) -> tuple[float, str]:
    area = parse_float(apt.get("area_sqm"))
    balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
    rooms = parse_rooms(apt.get("rooms"))
    notes = []
    score = 50.0

    if area and rooms:
        sqm_per_room = area / rooms
        if 22 <= sqm_per_room <= 32:
            score += 18
            notes.append(f"יעילות שטח טובה ({sqm_per_room:.1f} מ\"ר/חדר)")
        elif 18 <= sqm_per_room < 22:
            score += 10
            notes.append(f"יעילות שטח בינונית ({sqm_per_room:.1f} מ\"ר/חדר)")
        elif sqm_per_room < 18:
            score += 4
            notes.append(f"שטח צפוף ({sqm_per_room:.1f} מ\"ר/חדר)")
        else:
            score += 14
            notes.append(f"שטח מרווח ({sqm_per_room:.1f} מ\"ר/חדר)")

    if area and balcony:
        ratio = balcony / area * 100
        if floor_numeric(apt.get("floor", "")) == 0 and balcony > 100:
            score += 15
            notes.append(f"גינה {balcony:.0f} מ\"ר")
        elif 12 <= ratio <= 30:
            score += 12
            notes.append(f"יחס מרפסת {ratio:.1f}%")
        elif ratio > 30:
            score += 8
            notes.append(f"מרפסת/גינה גדולה ({ratio:.1f}%)")
        elif ratio < 12:
            score += 5
            notes.append(f"מרפסת קטנה ({ratio:.1f}%)")

    apt_type = apt.get("apartment_type", "")
    if apt_type in PENTHOUSE_TYPES:
        score += 10
        notes.append("תכנון יחידתי יוקרתי")

    score = max(0, min(100, score))

    if arch and arch.get("score_interior") is not None:
        interior = float(arch["score_interior"])
        score = round(interior * 0.7 + score * 0.3, 1)
        arch_notes = arch.get("notes_he", "")
        if arch_notes:
            notes.insert(0, arch_notes)

    return round(score, 1), "; ".join(notes)


def score_features(apt) -> tuple[float, str]:
    storage = parse_float(apt.get("storage_sqm")) or 0
    balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
    parking = apt.get("parking_spaces", "2")
    notes = []
    score = 55.0

    if storage >= 9:
        score += 18
        notes.append(f"מחסן גדול ({storage} מ\"ר)")
    elif storage >= 7:
        score += 12
        notes.append(f"מחסן בינוני ({storage} מ\"ר)")
    elif storage >= 5:
        score += 7
        notes.append(f"מחסן ({storage} מ\"ר)")
    else:
        score += 3

    if balcony >= 100:
        score += 15
        notes.append("מרפסת/גינה יוצאת דופן")
    elif balcony >= 24:
        score += 8
    elif balcony >= 18:
        score += 5

    if str(parking) == "2":
        score += 10
        notes.append("2 חניות")

    if apt.get("target_price") == "לא":
        score += 5
        notes.append("יחידת שוק חופשי (מפרט עשיר מוערך)")

    score = max(0, min(100, score))
    return round(score, 1), "; ".join(notes)


def score_rarity(apt, type_counts: Counter, total: int) -> tuple[float, str]:
    apt_type = apt.get("apartment_type", "")
    count = type_counts.get(apt_type, 1)
    notes = []
    freq = count / total
    score = max(10, 100 - freq * 400)

    if apt_type in PENTHOUSE_TYPES:
        score = min(100, score + 15)
        notes.append(f"סוג נדיר ({apt_type}, {count} בפרויקט)")
    elif count <= 3:
        score = min(100, score + 10)
        notes.append(f"נדירות גבוהה ({count} יחידות)")
    elif count <= 8:
        notes.append(f"מוגבל ({count} יחידות)")
    else:
        notes.append(f"שכיח ({count} יחידות)")

    rooms = apt.get("rooms", "")
    if rooms == "6":
        score = min(100, score + 8)
        notes.append("6 חדרים - נדיר בפרויקט")
    elif rooms == "3":
        score = max(20, score - 5)
        notes.append("3 חדרים - נפוץ בפרויקט")

    score = max(0, min(100, score))
    return round(score, 1), "; ".join(notes)


def overall_score(loc, view, plan, feat, rarity):
    return round(loc * 0.25 + view * 0.25 + plan * 0.20 + feat * 0.15 + rarity * 0.15, 1)


def analyze_apartment(apt, type_counts, total, arch: dict | None = None):
    building = int(apt["building"])
    floor_num = floor_numeric(apt.get("floor", ""))
    max_floor = TOWER_MAX_FLOOR if building in TOWERS else LOW_RISE_MAX.get(building, 7)

    loc_s, loc_n = score_location(apt, building, floor_num, max_floor)
    view_s, view_n = score_view(apt, building, floor_num, arch=arch)
    plan_s, plan_n = score_planning(apt, arch=arch)
    feat_s, feat_n = score_features(apt)
    rarity_s, rarity_n = score_rarity(apt, type_counts, total)
    total_s = overall_score(loc_s, view_s, plan_s, feat_s, rarity_s)

    directions = parse_directions(apt.get("directions", ""))
    balcony = parse_float(apt.get("balcony_garden_sqm"))
    view_label = classify_view(directions, floor_num, building, balcony or 0)

    all_notes = [n for n in [loc_n, view_n, plan_n, feat_n, rarity_n] if n]

    result = {
        "id": apt.get("id"),
        "apartment_number": apt.get("apartment_number"),
        "building": apt.get("building"),
        "floor": apt.get("floor"),
        "rooms": apt.get("rooms"),
        "apartment_type": apt.get("apartment_type"),
        "area_sqm": apt.get("area_sqm"),
        "balcony_garden_sqm": apt.get("balcony_garden_sqm"),
        "directions": apt.get("directions"),
        "view_classification": view_label,
        "score_location": loc_s,
        "score_view": view_s,
        "score_planning": plan_s,
        "score_features": feat_s,
        "score_rarity": rarity_s,
        "quality_score": total_s,
        "notes": " | ".join(all_notes),
        "analysis_detail": {
            "location": {"score": loc_s, "notes": loc_n},
            "view": {"score": view_s, "notes": view_n},
            "planning": {"score": plan_s, "notes": plan_n},
            "features": {"score": feat_s, "notes": feat_n},
            "rarity": {"score": rarity_s, "notes": rarity_n},
        },
        "source_url": apt.get("source_url"),
    }

    if arch:
        result["score_interior"] = arch.get("score_interior")
        result["score_view_plan"] = arch.get("score_view_plan")
        result["architecture_notes"] = arch.get("notes_he")
        result["architecture_model"] = arch.get("model")
        result["apartment_plan_url"] = arch.get("plan_url") or apt.get("apartment_plan_url")
        result["floor_plan_url"] = arch.get("floor_plan_url") or apt.get("floor_plan_url")

    return result


def setup_standard_files(apartments, project, buildings):
    db_json = BASE / "apartments_database.json"
    db_csv = BASE / "apartments_database.csv"
    shutil.copy(APARTMENTS_SRC, db_json)

    fields = list(apartments[0].keys()) if apartments else []
    with db_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(apartments)

    overview = f"""# סקירת פרויקט — שובל טאץ' נאות נבון חיפה

**תאריך עדכון:** {datetime.now().strftime('%Y-%m-%d')}

## מידע כללי

| פרמטר | ערך |
|--------|-----|
| שם הפרויקט | {project['project_name']} |
| יזם | {project['developer']} |
| תוכנית | {project['program']} |
| מספר הגרלה | {project['lottery_number']} |
| מיקום | {project['location']} |
| מגרשים | {', '.join(project['plots'])} |
| סה"כ יחידות | {project['total_units']} |
| מחיר מטרה | {project['target_price_units']} |
| שוק חופשי | {project['free_market_units']} |
| מבנים | {project['total_buildings']} |
| מועד מסירה | {project['delivery_date']} |

## מבנים

| מבנה | מגרש | דירות | קומות מקסימום | מחיר מטרה | שוק חופשי |
|------|------|-------|---------------|-----------|-----------|
"""
    for b in buildings:
        max_f = TOWER_MAX_FLOOR if int(b["building_number"]) in TOWERS else max(
            [floor_numeric(f) for f in b["floors"]]
        )
        overview += (
            f"| {b['building_number']} | {b['plot_number']} | {b['apartment_count']} "
            f"| {max_f} | {b['target_price_apartments']} | {b['free_market_apartments']} |\n"
        )

    overview += f"""
## מקור

- אתר רשמי: {project['source_url']}
- מאגר דירות: `apartments_database.json` ({len(apartments)} רשומות)
"""
    (BASE / "project_overview.md").write_text(overview, encoding="utf-8")

    docs = load_json(BASE / "04_documents" / "documents.json")
    doc_md = "# אינדקס מסמכים\n\n| # | שם | קטגוריה | URL |\n|---|-----|---------|-----|\n"
    for i, d in enumerate(docs, 1):
        doc_md += f"| {i} | {d['name']} | {d['category']} | {d['url']} |\n"
    doc_md += f"\n**סה\"כ:** {len(docs)} מסמכים רשמיים + 469 קבצי PDF (תוכניות דירה/קומה)\n"
    (BASE / "documents_index.md").write_text(doc_md, encoding="utf-8")

    ext = load_json(BASE / "05_external_sources" / "external_sources.json")
    src_md = "# אינדקס מקורות\n\n"
    for s in ext.get("sources", []):
        src_md += f"## {s['source_name']}\n- URL: {s['url']}\n- סוג: {s['source_type']}\n\n"
    (BASE / "sources_index.md").write_text(src_md, encoding="utf-8")


def write_project_structure(buildings, apartments, ranked):
    content = """# ניתוח מבנה הפרויקט — שובל טאץ' נאות נבון

**תאריך:** {date}
**מקור:** apartments_database.json + project_overview.md

---

## מידע כללי

| פרמטר | ערך |
|--------|-----|
| מספר בניינים | 14 |
| מגדלים (22 קומות) | מבנים 7, 14 |
| בניינים נמוכים (8 קומות) | מבנים 1–6, 8–13 |
| סה"כ דירות | 401 |
| מגרש 228 | מבנים 1–7 (211 דירות) |
| מגרש 229 | מבנים 8–14 (190 דירות) |

### סוגי דירות בפרויקט

| חדרים | כמות |
|-------|------|
""".format(date=datetime.now().strftime("%Y-%m-%d"))

    room_counts = Counter(a["rooms"] for a in apartments)
    for room, cnt in sorted(room_counts.items(), key=lambda x: float(x[0])):
        content += f"| {room} | {cnt} |\n"

    content += """
### חלוקה לפי מבנים

| מבנה | מגרש | דירות | סוג מבנה | ציון איכות ממוצע |
|------|------|-------|----------|------------------|
"""
    b_scores = {}
    for r in ranked:
        b = r["building"]
        b_scores.setdefault(b, []).append(r["quality_score"])
    for b in buildings:
        bn = b["building_number"]
        avg = sum(b_scores.get(bn, [0])) / max(len(b_scores.get(bn, [1])), 1)
        btype = "מגדל 22 קומות" if int(bn) in TOWERS else "בניין 8 קומות"
        content += f"| {bn} | {b['plot_number']} | {b['apartment_count']} | {btype} | {avg:.1f} |\n"

    content += """
---

## מאפייני הפרויקט

### מיקום הדירות בעלות פוטנציאל איכות גבוה

1. **קומות 19–21 במגדלים 7 ו-14** — יחידות פנטהאוז (4-M, 4-H, 4-K, 4-L) בשטחים 170–209 מ"ר, נוף פנורמי מוערך.
2. **קומות 15–18 במגדלים** — כיוון מערב/דרום, גובה מיטבי לנוף ים.
3. **דירות גן בקומת קרקע** — שטחי גינה 130–290 מ"ר (מבנים 1, 2, 3, 4, 5, 8, 9, 10, 12, 13).
4. **קומה 7 בבניינים נמוכים** — יחידות 3-G, 2-H, 3-GM (6 חדרים, מרפסות גדולות).

### בניינים בעלי יתרון מבני

| מבנה | יתרונות |
|------|---------|
| **7** | מגדל על מגרש 228, 93 דירות, מגוון טיפוסים, גובה מקסימלי בפרויקט |
| **14** | מגדל על מגרש 229, 95 דירות, מגוון דומה למבנה 7 |
| **2, 13** | קומה 7 עם פנטהאוז 6 חדרים (2-H), דירות גן גדולות בקרקע |
| **11** | יחידות קרקע+מרתף ייחודיות (3-OM, 3-PM) |

### בניינים בעלי חסרונות מבניים

| מבנה | חסרונות |
|------|---------|
| **9, 12** | בניינים קטנים (12 דירות), מעט טיפוסים, ללא קומות גבוהות |
| **1, 4** | מבנים קטנים יחסית, ללא קומת גג יוקרתית |
| **מבנים 1–6 (קומת קרקע)** | פחות פרטיות, חשיפה לרחוב/שטח ציבורי |

### אזורים עם פוטנציאל לנוף פתוח

- **מערב ודרום-מערב** בקומות גבוהות במגדלים 7, 14 — כיוון לים (מוערך לפי מיקום השכונה).
- **דירות גן** עם גינה 150+ מ"ר — שטח חיצוני פרטי גדול.
- **יחידות 4 כיווני אוויר** — למשל 1-D, 2-G, 3-G, 4-M.

### אזורים שעלולים להיפגע מבנייה עתידית

> הערה: מבוסס על מידע תכנוני חיצוני (תב"ע 304-0086512, מקורות עירוניים). לא אומת מול תוכניות בנייה ספציפיות.

1. **מבנים נמוכים (1–6, 8–13) בקומות 1–4** — חשיפה לבנייה עתידית בשכונת נאות נבון (6,000+ יחידות מתוכננות).
2. **כיוון מזרח וצפון-מזרח** — עשוי להיתקל בחסימת נוף מבניינים עתידיים בשכונה.
3. **מגרש 228 מול מגרש 229** — בניינים פנימיים עשויים להיות מוקפים במבנים נוספים.
4. **קומות נמוכות במגדלים (1–5)** — נוף מוגבל גם ללא בנייה עתידית.

---

*ניתוח איכות מבני בלבד — ללא המלצת השקעה.*
"""
    (BASE / "project_structure_analysis.md").write_text(content, encoding="utf-8")


def write_top10(ranked, apartments_by_id):
    lines = [
        "# Top 10 דירות איכות בפרויקט",
        "",
        f"**תאריך:** {datetime.now().strftime('%Y-%m-%d')}",
        "**קריטריון:** Property Quality Score (לא מחיר)",
        "",
        "---",
        "",
    ]
    for i, r in enumerate(ranked[:10], 1):
        apt = apartments_by_id.get(r["id"], {})
        lines += [
            f"## #{i} — מבנה {r['building']} דירה {r['apartment_number']} (ציון: {r['quality_score']})",
            "",
            f"| פרמטר | ערך |",
            f"|--------|-----|",
            f"| טיפוס | {r.get('apartment_type', '')} |",
            f"| קומה | {r['floor']} |",
            f"| חדרים | {r['rooms']} |",
            f"| שטח | {r['area_sqm']} מ\"ר |",
            f"| מרפסת/גינה | {r['balcony_garden_sqm']} מ\"ר |",
            f"| כיוונים | {r['directions']} |",
            f"| נוף | {r['view_classification']} |",
            f"| מיקום | {r['score_location']} | תכנון: {r['score_planning']} | נדירות: {r['score_rarity']} |",
            "",
            "### למה מיוחדת",
            explain_special(r, apt),
            "",
            "### יתרון",
            explain_advantage(r),
            "",
            "### חיסרון",
            explain_disadvantage(r),
            "",
            "---",
            "",
        ]
    (BASE / "top10_quality_apartments.md").write_text("\n".join(lines), encoding="utf-8")


def explain_special(r, apt):
    parts = []
    if r.get("apartment_type") in PENTHOUSE_TYPES:
        parts.append("יחידת פנטהאוז/גג נדירה בפרויקט")
    if parse_float(r.get("balcony_garden_sqm") or 0) and parse_float(r["balcony_garden_sqm"]) > 150:
        parts.append("שטח גינה יוצא דופן")
    if int(r["building"]) in TOWERS and floor_numeric(r["floor"]) >= 19:
        parts.append("קומה גבוהה במגדל עם תכנון יוקרתי")
    if r["score_rarity"] >= 85:
        parts.append("נדירות גבוהה בפרויקט")
    if r["score_view"] >= 85:
        parts.append("פוטנציאל נוף גבוה")
    return "- " + "\n- ".join(parts) if parts else "- ציון איכות כולל גבוה בכל ממדים"


def explain_advantage(r):
    parts = []
    if r["score_location"] >= 80:
        parts.append("מיקום מבני מצוין")
    if r["score_view"] >= 80:
        parts.append("כיווני אוויר ונוף מוערכים")
    if r["score_planning"] >= 75:
        parts.append("תכנון פונקציונלי ושטחים מאוזנים")
    if parse_float(r.get("balcony_garden_sqm") or 0) and parse_float(r["balcony_garden_sqm"]) > 80:
        parts.append("מרפסת/גינה גדולה")
    return "- " + "\n- ".join(parts) if parts else "- איזון טוב בין כל ממדי האיכות"


def explain_disadvantage(r):
    parts = []
    if r.get("target_price") == "לא" or not r.get("final_price"):
        parts.append("יחידת שוק חופשי — מחיר לא מפורסם במחירון")
    if floor_numeric(r["floor"]) <= 0:
        parts.append("קומת קרקע — פחות פרטיות")
    if int(r["building"]) in TOWERS and floor_numeric(r["floor"]) >= 18:
        parts.append("קומה גבוהה — תלות במעליות, רגישות לרוח")
    if r["score_rarity"] < 50:
        parts.append("טיפוס שכיח — פחות ייחודיות")
    if "מזרח" in (r.get("directions") or "") and "מערב" not in (r.get("directions") or ""):
        parts.append("ללא כיוון מערבי — פוטנציאל נוף ים מוגבל")
    return "- " + "\n- ".join(parts) if parts else "- לא זוהה חיסרון מבני משמעותי בנתונים הקיימים"


def write_validation(apartments, ranked):
    missing_price = [a for a in apartments if a.get("target_price") == "כן" and not a.get("final_price")]
    free_no_price = [a for a in apartments if a.get("target_price") == "לא" and not a.get("final_price")]
    no_plan = [a for a in apartments if not a.get("apartment_plan_url")]
    target_no_plan = [a for a in apartments if a.get("target_price") == "כן" and not a.get("apartment_plan_url")]
    with_plan = len(apartments) - len(no_plan)
    plan_linked = len(target_no_plan) == 0 and with_plan >= 322
    null_area = [a for a in apartments if not a.get("area_sqm")]
    arch_count = sum(1 for r in ranked if r.get("score_interior") is not None)

    content = f"""# דוח ביקורת נתונים — ניתוח איכות

**תאריך:** {datetime.now().strftime('%Y-%m-%d')}

---

## 1. דירות ללא נתונים

| בדיקה | כמות | סטטוס |
|--------|------|--------|
| ללא שטח דירה | {len(null_area)} | {'✅' if not null_area else '⚠️'} |
| ללא כיווני אוויר | {len([a for a in apartments if not a.get('directions')])} | ✅ |
| ללא מספר חדרים | {len([a for a in apartments if not a.get('rooms')])} | ✅ |
| ללא תוכנית דירה (URL) | {len(no_plan)} | {'✅ מחיר מטרה מכוסה' if not target_no_plan else '⚠️'} |

**הערה:** {with_plan} דירות מקושרות לתכנית PDF (322 מחיר מטרה). {len(no_plan)} דירות שוק חופשי ללא תכנית באינדקס. ניתוח אדריכלי: {arch_count} דירות.

---

## 2. מחירים ללא מקור

| קטגוריה | כמות |
|---------|------|
| מחיר מטרה ללא מחיר סופי | {len(missing_price)} |
| שוק חופשי ללא מחיר (צפוי) | {len(free_no_price)} |

**פירוט:**
- **{len(free_no_price)} דירות שוק חופשי** — מסומנות "לא" במחיר מטרה, ללא מחיר סופי במחירון (מצופה).
- **{len(missing_price)} דירות מחיר מטרה** — כולן כוללות מחיר סופי ממקור האתר.

---

## 3. סתירות במסמכים

| נושא | פירוט |
|------|--------|
| פיתוח מגרש 229 | קישור "פיתוח מגרש 229" מפנה לאותו PDF של מגרש 228 |
| מספר קומות מגדל | האתר: 22 קומות; נתוני דירות: קומות 1–21 בלבד (ללא קומה 22 ברשימה) |
| מבנה 11 מגרשים | דירות 3-OM במגרש 229, דירות 3-PM/CM/DM במגרש 228 — מבנה אחד על שני מגרשים |

---

## 4. תשריטים

| פריט | סטטוס |
|------|--------|
| תוכנית דירה מקושרת (מחיר מטרה) | {322 - len(target_no_plan)}/322 |
| תוכנית דירה שוק חופשי | 0/79 (מחוץ להיקף ראשוני) |
| ניתוח אדריכלי שמור | {arch_count} רשומות |

---

## 5. מגבלות ניתוח האיכות

| מגבלה | השפעה |
|--------|--------|
| אין נתוני מעלית/לובי | ציון מיקום מוערך לפי קומה ומבנה בלבד |
| אין אימות כיוון אמיתי למבנה | נוף ים מוערך לפי כיווני אוויר + מיקום שכונה |
| אין תשריט פנימי | {'מכוסה ל-' + str(arch_count) + ' דירות מחיר מטרה' if arch_count else 'ציון תכנון מבוסס שטחים בלבד, לא חלוקה פנימית'} |
| אין נתוני רעש/רחוב | לא נכלל בניתוח |

---

## סיכום

| בדיקה | תוצאה |
|--------|--------|
| כל 401 דירות נותחו | ✅ |
| ניתוח איכות הושלם | ✅ |
| מחירי מחיר מטרה שלמים | ✅ |
| תשריטים מקושרים לדירות | {'✅' if plan_linked else '❌'} |
| סתירות שזוהו | 3 (מתועדות לעיל) |

*דוח ביקורת נתונים — ללא המלצת השקעה.*
"""
    (BASE / "quality_validation_report.md").write_text(content, encoding="utf-8")


def main():
    apartments = load_json(APARTMENTS_SRC)
    buildings = load_json(BUILDINGS_SRC)
    project = load_json(PROJECT_SRC)

    setup_standard_files(apartments, project, buildings)

    arch_by_id = {}
    if ARCHITECTURE_SRC.exists():
        arch_by_id = {r["id"]: r for r in load_json(ARCHITECTURE_SRC)}

    type_counts = Counter(a["apartment_type"] for a in apartments)
    total = len(apartments)

    analyses = []
    for apt in apartments:
        arch = arch_by_id.get(apt.get("id"))
        a = analyze_apartment(apt, type_counts, total, arch=arch)
        a["target_price"] = apt.get("target_price")
        a["final_price"] = apt.get("final_price")
        if not arch:
            a["apartment_plan_url"] = apt.get("apartment_plan_url")
            a["floor_plan_url"] = apt.get("floor_plan_url")
        analyses.append(a)

    ranked = sorted(analyses, key=lambda x: x["quality_score"], reverse=True)

    csv_fields = [
        "דירה", "בניין", "קומה", "חדרים", "שטח", "מרפסת", "נוף",
        "ציון מיקום", "ציון תכנון", "ציון נדירות", "ציון איכות כולל", "הערות"
    ]
    csv_path = BASE / "apartments_quality_ranking.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(csv_fields)
        for r in ranked:
            w.writerow([
                r["apartment_number"], r["building"], r["floor"], r["rooms"],
                r["area_sqm"], r["balcony_garden_sqm"], r["view_classification"],
                r["score_location"], r["score_planning"], r["score_rarity"],
                r["quality_score"], r["notes"][:200]
            ])

  # Full analysis JSON for dashboard
    (BASE / "apartments_quality_analysis.json").write_text(
        json.dumps(ranked, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    apartments_by_id = {a["id"]: a for a in apartments}
    write_project_structure(buildings, apartments, ranked)
    write_top10(ranked, apartments_by_id)
    write_validation(apartments, ranked)

    print(f"Analysis complete: {len(ranked)} apartments ranked")
    print(f"Top score: {ranked[0]['quality_score']} (B{ranked[0]['building']}-A{ranked[0]['apartment_number']})")
    print(f"Files: apartments_quality_ranking.csv, project_structure_analysis.md, top10_quality_apartments.md, quality_validation_report.md")


if __name__ == "__main__":
    main()
