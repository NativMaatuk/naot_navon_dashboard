#!/usr/bin/env python3
"""Batch architectural interior + view analysis from apartment plan PDFs.

Results are saved to apartments_architecture_analysis.json for dashboard display.
Supports OpenAI Vision when OPENAI_API_KEY is set; otherwise uses heuristic analysis.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path

from plan_utils import (
    APARTMENTS_JSON,
    BASE,
    dedup_fingerprint,
    download_plan,
    get_dedup_representatives,
    link_apartment_plans,
    load_json,
    render_pdf_first_page,
    save_json,
)

OUTPUT_JSON = BASE / "apartments_architecture_analysis.json"
REPORT_MD = BASE / "06_quality_check" / "architecture_analysis_report.md"

PENTHOUSE_TYPES = {
    "4-M", "4-H", "4-K", "4-L", "4-I",
    "3-G", "3-F", "3-FM", "3-GM",
    "2-H", "2-G", "2-F",
    "5-D",
}
TOWERS = {7, 14}
TOWER_MAX_FLOOR = 21

CHECKLIST_PROMPT = """נתח את תכנית הדירה המצורפת וענה ב-JSON בלבד (ללא טקסט נוסף) לפי הסכמה:
{
  "subscores": {
    "circulation": 0-100,
    "living_kitchen": 0-100,
    "bedrooms_privacy": 0-100,
    "bathroom_access": 0-100,
    "balcony_connection": 0-100,
    "room_proportions": 0-100,
    "dead_space": 0-100
  },
  "view_detail": {
    "living_faces_west": true/false,
    "balcony_faces_west": true/false,
    "bedrooms_face_north": true/false,
    "notes": "הערות קצרות בעברית על נוף וכיוונים"
  },
  "notes_he": "סיכום אדריכלי קצר בעברית (2-3 משפטים)"
}

קריטריונים:
- circulation: יעילות מעברים ומסדרונות
- living_kitchen: רציפות סלון-מטבח ופתיחות
- bedrooms_privacy: הפרדת חדרי שינה מכניסה/רעש
- bathroom_access: נגישות שירותים
- balcony_connection: חיבור מרפסת לסלון
- room_proportions: פרופורציות חדרים
- dead_space: פחות "שטח מת" = ציון גבוה יותר

כיווני אוויר רשומים בדירה: {directions}
"""


def parse_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return None


def parse_rooms(val) -> float | None:
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
    return [p for p in parts if p in ("צפון", "דרום", "מזרח", "מערב")]


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


def clamp(score: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, score))


def compute_interior_score(subscores: dict) -> float:
    if not subscores:
        return 50.0
    return round(sum(subscores.values()) / len(subscores), 1)


def compute_view_score(view_detail: dict, apt: dict, building: int, floor_num: int) -> float:
    directions = parse_directions(apt.get("directions", ""))
    score = 35.0

    if view_detail.get("living_faces_west"):
        score += 20
    elif "מערב" in directions:
        score += 12

    if view_detail.get("balcony_faces_west"):
        score += 12

    if "דרום" in directions:
        score += 10

    if len(directions) >= 3:
        score += 8

    if building in TOWERS and floor_num >= 12:
        score += 10

    balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
    if floor_num == 0 and balcony > 100:
        score += 8

    return round(clamp(score), 1)


def analyze_heuristic(apt: dict) -> dict:
    """Rule-based analysis using tabular data + type patterns."""
    directions = parse_directions(apt.get("directions", ""))
    building = int(apt.get("building", 0) or 0)
    floor_num = floor_numeric(apt.get("floor", ""))
    area = parse_float(apt.get("area_sqm"))
    balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
    rooms = parse_rooms(apt.get("rooms"))
    n_dirs = len(directions)
    apt_num = int(apt.get("apartment_number", 0) or 0)
    apt_type = apt.get("apartment_type", "")

    subscores: dict[str, float] = {}

    if area and rooms:
        spr = area / rooms
        if 24 <= spr <= 32:
            subscores["circulation"] = 82
        elif 20 <= spr < 24:
            subscores["circulation"] = 72
        elif spr > 32:
            subscores["circulation"] = 76
        else:
            subscores["circulation"] = 58
        subscores["room_proportions"] = subscores["circulation"]
        if spr < 20:
            subscores["dead_space"] = 48
        elif spr > 35:
            subscores["dead_space"] = 58
        else:
            subscores["dead_space"] = 76
    else:
        subscores["circulation"] = 55
        subscores["room_proportions"] = 55
        subscores["dead_space"] = 50

    lk = 62
    if n_dirs >= 3:
        lk += 14
    if area and balcony and 12 <= balcony / area * 100 <= 35:
        lk += 12
    subscores["living_kitchen"] = clamp(lk)

    bp = 58
    if n_dirs >= 3:
        bp += 16
    if apt_num > 2:
        bp += 10
    if floor_num >= 5:
        bp += 5
    subscores["bedrooms_privacy"] = clamp(bp)

    if rooms and rooms >= 5.5:
        subscores["bathroom_access"] = 80
    elif rooms and rooms >= 4:
        subscores["bathroom_access"] = 73
    else:
        subscores["bathroom_access"] = 65

    if balcony >= 30:
        subscores["balcony_connection"] = 82
    elif balcony >= 20:
        subscores["balcony_connection"] = 74
    elif balcony >= 12:
        subscores["balcony_connection"] = 66
    else:
        subscores["balcony_connection"] = 52

    if apt_type in PENTHOUSE_TYPES:
        for key in subscores:
            subscores[key] = clamp(subscores[key] + 5)

    living_west = "מערב" in directions and n_dirs >= 2
    balcony_west = "מערב" in directions
    bedrooms_north = "צפון" in directions and n_dirs >= 2

    view_notes = []
    if living_west:
        view_notes.append("סלון צפוי לפנות מערב (נוף ים)")
    if balcony_west:
        view_notes.append("מרפסת על כיוון מערב")
    if n_dirs >= 3:
        view_notes.append("יחידה רב-כיוונית")

    view_detail = {
        "living_faces_west": living_west,
        "balcony_faces_west": balcony_west,
        "bedrooms_face_north": bedrooms_north,
        "notes": "; ".join(view_notes),
    }

    interior_notes = []
    if subscores["circulation"] >= 75:
        interior_notes.append("יעילות מעברים טובה")
    if subscores["living_kitchen"] >= 75:
        interior_notes.append("סלון-מטבח מאוזן")
    if subscores["balcony_connection"] >= 75:
        interior_notes.append("מרפסת מחוברת היטב לסלון")
    if subscores["dead_space"] >= 70:
        interior_notes.append("מעט שטח מת")
    if apt_type in PENTHOUSE_TYPES:
        interior_notes.append("תכנון יחידתי יוקרתי")

    score_interior = compute_interior_score(subscores)
    score_view_plan = compute_view_score(view_detail, apt, building, floor_num)

    return {
        "subscores": {k: round(v, 1) for k, v in subscores.items()},
        "view_detail": view_detail,
        "notes_he": "; ".join(interior_notes) if interior_notes else "תכנון סטנדרטי",
        "score_interior": score_interior,
        "score_view_plan": score_view_plan,
        "model": "heuristic-v1",
    }


def analyze_vision(apt: dict, png_path: Path) -> dict | None:
    """Analyze plan image via OpenAI Vision API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    image_b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    directions = apt.get("directions", "—")
    prompt = CHECKLIST_PROMPT.format(directions=directions)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=800,
    )

    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    subscores = parsed.get("subscores", {})
    view_detail = parsed.get("view_detail", {})
    building = int(apt.get("building", 0) or 0)
    floor_num = floor_numeric(apt.get("floor", ""))

    return {
        "subscores": {k: round(float(v), 1) for k, v in subscores.items()},
        "view_detail": view_detail,
        "notes_he": parsed.get("notes_he", ""),
        "score_interior": compute_interior_score(subscores),
        "score_view_plan": compute_view_score(view_detail, apt, building, floor_num),
        "model": os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
    }


def analyze_apartment(apt: dict, mode: str = "auto", cache: bool = True) -> dict:
    """Analyze one apartment; returns architecture record."""
    result = None
    plan_url = apt.get("apartment_plan_url")
    local_pdf = None

    if cache and plan_url:
        local_pdf = download_plan(apt)

    use_vision = mode == "vision" or (mode == "auto" and os.environ.get("OPENAI_API_KEY"))

    if use_vision and local_pdf:
        png = render_pdf_first_page(local_pdf)
        if png:
            result = analyze_vision(apt, png)

    if result is None:
        result = analyze_heuristic(apt)

    building = int(apt.get("building", 0) or 0)
    floor_num = floor_numeric(apt.get("floor", ""))

    return {
        "id": apt["id"],
        "apartment_type": apt.get("apartment_type"),
        "building": apt.get("building"),
        "apartment_number": apt.get("apartment_number"),
        "plan_url": plan_url,
        "floor_plan_url": apt.get("floor_plan_url"),
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "model": result["model"],
        "score_interior": result["score_interior"],
        "score_view_plan": result["score_view_plan"],
        "subscores": result["subscores"],
        "view_detail": result["view_detail"],
        "notes_he": result["notes_he"],
        "deduped_from": None,
        "directions": apt.get("directions"),
        "floor": apt.get("floor"),
        "floor_num": floor_num,
        "building_num": building,
    }


def run_batch(
    apartments: list[dict],
    mode: str = "auto",
    sample: int | None = None,
    cache: bool = True,
    resume: bool = True,
) -> tuple[list[dict], dict]:
    existing: dict[str, dict] = {}
    if resume and OUTPUT_JSON.exists():
        existing = {r["id"]: r for r in load_json(OUTPUT_JSON)}

    reps = get_dedup_representatives(apartments)
    rep_items = list(reps.items())
    if sample:
        rep_items = rep_items[:sample]

    rep_results: dict[tuple, dict] = {}
    for key, rep in rep_items:
        if resume and rep["id"] in existing:
            rep_results[key] = existing[rep["id"]]
        else:
            rep_results[key] = analyze_apartment(rep, mode=mode, cache=cache)

    results: list[dict] = []
    analyzed_direct = 0
    copied = 0
    sample_keys = {k for k, _ in rep_items} if sample else None

    for apt in apartments:
        if apt.get("target_price") != "כן" or not apt.get("apartment_plan_url"):
            continue
        key = dedup_fingerprint(apt)
        if sample_keys is not None and key not in sample_keys:
            continue
        if key not in rep_results:
            continue

        record = dict(rep_results[key])
        source_id = rep_results[key]["id"]
        if source_id != apt["id"]:
            record = {**record, "id": apt["id"], "deduped_from": source_id}
            copied += 1
        else:
            analyzed_direct += 1

        record["apartment_number"] = apt.get("apartment_number")
        record["building"] = apt.get("building")
        record["plan_url"] = apt.get("apartment_plan_url")
        record["floor_plan_url"] = apt.get("floor_plan_url")
        results.append(record)

    results.sort(key=lambda r: r["id"])
    meta = {
        "representatives_analyzed": len(rep_items),
        "unique_fingerprints": len(reps),
        "total_output": len(results),
        "copied_from_dedup": copied,
        "analyzed_direct": analyzed_direct,
        "mode": mode,
    }
    return results, meta


def write_report(stats: dict, meta: dict) -> None:
    content = f"""# דוח ניתוח אדריכלי

**תאריך:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

| מדד | ערך |
|-----|-----|
| טביעות אצבע ייחודיות | {meta['unique_fingerprints']} |
| נציגים שנותחו | {meta['representatives_analyzed']} |
| סה"כ רשומות בפלט | {meta['total_output']} |
| הועתקו מדה-דופ | {meta['copied_from_dedup']} |
| מודל | {meta.get('model', meta.get('mode', '—'))} |

## הערות
- ניתוח רץ offline ונשמר ב-`apartments_architecture_analysis.json`
- הדשבורד קורא את הקובץ בלבד (ללא ניתוח בזמן ריצה)
- להפעלת Vision: הגדר `OPENAI_API_KEY` והרץ עם `--mode vision`
"""
    REPORT_MD.write_text(content, encoding="utf-8")
    print(
        f"Architecture report: {meta.get('total_output', 0)} records, "
        f"{meta.get('representatives_analyzed', 0)} reps, model={meta.get('model', '—')}"
    )


def main():
    parser = argparse.ArgumentParser(description="Batch architectural plan analysis")
    parser.add_argument("--mode", choices=["auto", "heuristic", "vision"], default="auto")
    parser.add_argument("--sample", type=int, default=None, help="Analyze only N representative fingerprints")
    parser.add_argument("--no-cache", action="store_true", help="Skip PDF download")
    parser.add_argument("--no-resume", action="store_true", help="Re-analyze all")
    parser.add_argument("--link", action="store_true", help="Re-link plan URLs before analysis")
    args = parser.parse_args()

    apartments = load_json(APARTMENTS_JSON)
    if args.link:
        link_apartment_plans(apartments)
        save_json(APARTMENTS_JSON, apartments)

    results, meta = run_batch(
        apartments,
        mode=args.mode,
        sample=args.sample,
        cache=not args.no_cache,
        resume=not args.no_resume,
    )

    save_json(OUTPUT_JSON, results)
    model = results[0]["model"] if results else args.mode
    meta["model"] = model
    write_report({}, meta)

    print(f"Saved {len(results)} records to {OUTPUT_JSON.name}")


if __name__ == "__main__":
    main()
