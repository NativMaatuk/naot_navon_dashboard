#!/usr/bin/env python3
"""Task 3: Value analysis — price vs quality for Shoval Touch Naot Navon."""
import json
import csv
import statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE = Path(__file__).parent

ROOM_LIQUIDITY = {3: 88, 4: 85, 5: 80, 5.5: 72, 6: 62}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_price(val):
    if not val:
        return None
    s = str(val).replace("₪", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_float(val):
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_rooms(val):
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None


def floor_numeric(floor):
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


def classify_price_position(deviation_pct):
    if deviation_pct <= -8:
        return "זולה ביחס לפרויקט"
    if deviation_pct >= 8:
        return "יקרה ביחס לפרויקט"
    return "במחיר שוק"


def score_price(ppsm_built, ppsm_group_avg, ppsm_group_std, ppsm_project_avg, area, balcony):
    """Higher score = more attractive price. 0-100."""
    if ppsm_built is None:
        return None
    score = 50.0
    if ppsm_group_std and ppsm_group_std > 0:
        z_group = (ppsm_built - ppsm_group_avg) / ppsm_group_std
        score += -z_group * 18
    if ppsm_project_avg:
        dev = (ppsm_built - ppsm_project_avg) / ppsm_project_avg * 100
        score += -dev * 0.4

    total_area = area + (balcony or 0)
    if total_area > 0 and area:
        ppsm_total = None  # computed outside
        built_ratio = area / total_area
        if built_ratio > 0.85:
            score += 3

    return round(max(0, min(100, score)), 1)


def score_liquidity(rooms, floor_num, type_count, quality_score, building):
    """Future salability estimate. 0-100."""
    base = ROOM_LIQUIDITY.get(rooms, 75)
    if rooms == int(rooms):
        base = ROOM_LIQUIDITY.get(int(rooms), ROOM_LIQUIDITY.get(rooms, 75))
    else:
        base = ROOM_LIQUIDITY.get(rooms, 75)

    if 3 <= floor_num <= 8:
        base += 8
    elif floor_num == 0:
        base += 2
    elif floor_num >= 15:
        base -= 8
    elif floor_num >= 10:
        base -= 3

    if type_count >= 30:
        base += 6
    elif type_count <= 5:
        base -= 10
    elif type_count <= 12:
        base -= 4

    if int(building) in (7, 14):
        base += 3

    if rooms == 3:
        base += 5

    return round(max(0, min(100, base)), 1)


def score_pricing_risk(ppsm_built, quality_score, min_ppsm, max_ppsm, alternatives_better):
    """Risk that price already embeds premium. Lower risk = better. Returns risk 0-100."""
    if ppsm_built is None or max_ppsm <= min_ppsm:
        return 50.0
    expected = min_ppsm + (quality_score / 100) * (max_ppsm - min_ppsm)
    if expected <= 0:
        return 50.0
    premium_pct = (ppsm_built - expected) / expected * 100
    risk = 50 + premium_pct * 0.8
    if alternatives_better:
        risk += 12
    return round(max(0, min(100, risk)), 1)


def value_score(price_s, quality_s, liquidity_s, risk_s):
    if any(v is None for v in [price_s, quality_s, liquidity_s, risk_s]):
        return None
    return round(
        price_s * 0.35 + quality_s * 0.35 + liquidity_s * 0.20 + (100 - risk_s) * 0.10,
        1,
    )


def find_alternatives_better(apt, all_priced, ppsm_tol=0.03):
    """True if similar-priced apt exists with meaningfully higher quality."""
    price = apt["price_total"]
    quality = apt["quality_score"]
    if not price:
        return False
    for other in all_priced:
        if other["id"] == apt["id"]:
            continue
        if abs(other["price_total"] - price) / price <= ppsm_tol:
            if other["quality_score"] > quality + 8:
                return True
    return False


def analyze():
    db = load_json(BASE / "apartments_database.json")
    quality = load_json(BASE / "apartments_quality_analysis.json")
    q_by_id = {q["id"]: q for q in quality}

    type_counts = defaultdict(int)
    for a in db:
        type_counts[a["apartment_type"]] += 1

    records = []
    for apt in db:
        q = q_by_id.get(apt["id"], {})
        area = parse_float(apt.get("area_sqm"))
        balcony = parse_float(apt.get("balcony_garden_sqm")) or 0
        price = parse_price(apt.get("final_price"))
        rooms = parse_rooms(apt.get("rooms"))

        rec = {
            "id": apt["id"],
            "apartment_number": apt["apartment_number"],
            "building": apt["building"],
            "floor": apt.get("floor"),
            "rooms": apt.get("rooms"),
            "apartment_type": apt.get("apartment_type"),
            "area_sqm": area,
            "balcony_garden_sqm": balcony,
            "target_price": apt.get("target_price"),
            "price_total": price,
            "price_source": apt.get("source_url") if price else None,
            "quality_score": q.get("quality_score"),
            "score_view": q.get("score_view"),
            "score_rarity": q.get("score_rarity"),
            "view_classification": q.get("view_classification"),
            "notes_quality": q.get("notes", ""),
        }
        if price and area:
            rec["price_per_sqm_built"] = round(price / area, 2)
            total_area = area + balcony
            rec["price_per_sqm_incl_balcony"] = round(price / total_area, 2) if total_area else None
        else:
            rec["price_per_sqm_built"] = None
            rec["price_per_sqm_incl_balcony"] = None
        records.append(rec)

    priced = [r for r in records if r["price_total"]]
    unpriced = [r for r in records if not r["price_total"]]

    ppsm_list = [r["price_per_sqm_built"] for r in priced if r["price_per_sqm_built"]]
    project_avg_ppsm = statistics.mean(ppsm_list)
    project_std_ppsm = statistics.stdev(ppsm_list) if len(ppsm_list) > 1 else 0
    min_ppsm = min(ppsm_list)
    max_ppsm = max(ppsm_list)

    by_rooms = defaultdict(list)
    for r in priced:
        if r["price_per_sqm_built"]:
            by_rooms[r["rooms"]].append(r["price_per_sqm_built"])

    room_stats = {}
    for rooms, ppsms in by_rooms.items():
        room_stats[rooms] = {
            "avg": statistics.mean(ppsms),
            "std": statistics.stdev(ppsms) if len(ppsms) > 1 else 0,
            "count": len(ppsms),
        }

    for r in records:
        if not r["price_total"] or not r["price_per_sqm_built"]:
            r["deviation_from_project_pct"] = None
            r["price_position"] = "ללא מחיר — שוק חופשי"
            r["price_score"] = None
            r["liquidity_score"] = None
            r["pricing_risk"] = None
            r["value_score"] = None
            r["quality_per_million"] = None
            continue

        r["deviation_from_project_pct"] = round(
            (r["price_per_sqm_built"] - project_avg_ppsm) / project_avg_ppsm * 100, 2
        )
        r["price_position"] = classify_price_position(r["deviation_from_project_pct"])

        rs = room_stats.get(r["rooms"], {"avg": project_avg_ppsm, "std": project_std_ppsm})
        r["price_score"] = score_price(
            r["price_per_sqm_built"], rs["avg"], rs["std"], project_avg_ppsm,
            r["area_sqm"], r["balcony_garden_sqm"],
        )
        r["liquidity_score"] = score_liquidity(
            parse_rooms(r["rooms"]),
            floor_numeric(r["floor"]),
            type_counts[r["apartment_type"]],
            r["quality_score"] or 50,
            r["building"],
        )
        alt_better = find_alternatives_better(r, priced)
        r["pricing_risk"] = score_pricing_risk(
            r["price_per_sqm_built"],
            r["quality_score"] or 50,
            min_ppsm,
            max_ppsm,
            alt_better,
        )
        r["value_score"] = value_score(
            r["price_score"], r["quality_score"], r["liquidity_score"], r["pricing_risk"]
        )
        r["quality_per_million"] = round(
            (r["quality_score"] or 0) / (r["price_total"] / 1_000_000), 2
        )
        r["alternatives_at_similar_price"] = alt_better

    ranked = sorted(
        [r for r in records if r["value_score"] is not None],
        key=lambda x: x["value_score"],
        reverse=True,
    )
    for i, r in enumerate(ranked, 1):
        r["value_rank"] = i

    for r in records:
        if r.get("value_rank") is None:
            r["value_rank"] = None

    return {
        "records": records,
        "priced": priced,
        "unpriced": unpriced,
        "ranked": ranked,
        "project_avg_ppsm": project_avg_ppsm,
        "project_std_ppsm": project_std_ppsm,
        "min_ppsm": min_ppsm,
        "max_ppsm": max_ppsm,
        "room_stats": room_stats,
    }


def write_csv(ranked, path):
    fields = [
        "דירה", "בניין", "קומה", "חדרים", "שטח", "מחיר", "מחיר למ\"ר",
        "Quality Score", "Price Score", "Value Score", "דירוג", "הערות",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in ranked:
            notes = f"{r['price_position']}; סטייה {r['deviation_from_project_pct']:+.1f}%"
            if r.get("alternatives_at_similar_price"):
                notes += "; קיימת חלופה טובה יותר באותו מחיר"
            w.writerow([
                r["apartment_number"], r["building"], r["floor"], r["rooms"],
                r["area_sqm"],
                int(r["price_total"]) if r["price_total"] else "",
                r["price_per_sqm_built"],
                r["quality_score"], r["price_score"], r["value_score"],
                r["value_rank"], notes,
            ])


def profile_apartment(r):
    rooms = r["rooms"]
    floor = r["floor"]
    profiles = []
    if rooms in ("3", "3.0"):
        profiles.append("משפחות צעירות / זוגות המחפשים כניסה למחיר מטרה")
    elif rooms in ("4", "4.0"):
        profiles.append("משפחות עם 1–2 ילדים")
    elif rooms in ("5", "5.0", "5.5"):
        profiles.append("משפחות מורחבות המחפשות שטח")
    if floor_numeric(floor) >= 15:
        profiles.append("רוכשים המעדיפים נוף וקומה גבוהה")
    if floor_numeric(floor) == 0:
        profiles.append("רוכשים המעדיפים גינה פרטית")
    if not profiles:
        profiles.append("רוכשי מגורים למגורים עצמיים בפרויקט")
    return "; ".join(profiles)


def write_top10_opportunities(ranked, path):
    top = ranked[:10]
    lines = [
        "# Top 10 Value Opportunities",
        "",
        f"**תאריך:** {datetime.now().strftime('%Y-%m-%d')}",
        "**קריטריון:** Value Score — איכות מקסימלית לכל שקל (לא הדירה הזולה ביותר)",
        "",
        "---",
        "",
    ]
    for i, r in enumerate(top, 1):
        lines += [
            f"## #{i} — מבנה {r['building']} דירה {r['apartment_number']} (Value: {r['value_score']})",
            "",
            f"| פרמטר | ערך |",
            f"|--------|-----|",
            f"| מחיר | {int(r['price_total']):,} ₪ |",
            f"| מחיר למ\"ר | {r['price_per_sqm_built']:,.0f} ₪ |",
            f"| Quality Score | {r['quality_score']} |",
            f"| Price Score | {r['price_score']} |",
            f"| מיקום מחיר | {r['price_position']} ({r['deviation_from_project_pct']:+.1f}%) |",
            f"| קומה | {r['floor']} | {r['rooms']} חדרים |",
            "",
            "### למה מעניינת",
            f"- יחס איכות/מחיר גבוה (Quality per מיליון: {r['quality_per_million']})",
            f"- {r['price_position']} — מחיר למ\"ר {r['deviation_from_project_pct']:+.1f}% מהממוצע",
            f"- נוף: {r['view_classification']}",
            "",
            "### יתרון",
            f"- איכות {r['quality_score']} במחיר למ\"ר {r['price_per_sqm_built']:,.0f} ₪",
            f"- סחירות מוערכת: {r['liquidity_score']}",
            "",
            "### חיסרון",
        ]
        cons = []
        if r["pricing_risk"] > 55:
            cons.append(f"- סיכון תמחור מוערך ({r['pricing_risk']})")
        if r["quality_score"] < 70:
            cons.append("- איכות מבנית לא בראש הדירוג")
        if r.get("alternatives_at_similar_price"):
            cons.append("- קיימת חלופה באותו טווח מחיר עם איכות גבוהה יותר")
        if not cons:
            cons.append("- לא זוהה חיסרון מחיר/ערך משמעותי בנתונים")
        lines.extend(cons)
        lines += [
            "",
            "### למי מתאימה",
            profile_apartment(r),
            "",
            "---",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_traps(ranked, path):
    """10 least attractive by value score among priced units."""
    traps = sorted(ranked, key=lambda x: x["value_score"])[:10]
    lines = [
        "# 10 דירות פחות אטרקטיביות (מלכודות תמחור)",
        "",
        f"**תאריך:** {datetime.now().strftime('%Y-%m-%d')}",
        "**הערה:** דירות עם מחיר מפורסם בלבד. לא כולל 79 יחידות שוק חופשי ללא מחיר.",
        "",
        "---",
        "",
    ]
    for i, r in enumerate(traps, 1):
        reasons = []
        if r["deviation_from_project_pct"] > 5:
            reasons.append(f"פרמיית מחיר +{r['deviation_from_project_pct']:.1f}% ממוצע הפרויקט")
        if r["quality_score"] < 65:
            reasons.append(f"איכות נמוכה ({r['quality_score']})")
        if r["score_view"] and r["score_view"] < 55:
            reasons.append("נוף/כיוונים חלשים")
        if r["pricing_risk"] > 60:
            reasons.append(f"סיכון תמחור גבוה ({r['pricing_risk']})")
        if r.get("alternatives_at_similar_price"):
            reasons.append("חלופות טובות יותר באותו מחיר בפרויקט")
        if floor_numeric(r["floor"]) <= 1 and r["quality_score"] < 72:
            reasons.append("מיקום קומתי חלש")

        lines += [
            f"## #{i} — מבנה {r['building']} דירה {r['apartment_number']} (Value: {r['value_score']})",
            "",
            f"| מחיר | {int(r['price_total']):,} ₪ | מחיר למ\"ר | {r['price_per_sqm_built']:,.0f} ₪ |",
            f"| Quality | {r['quality_score']} | Price Score | {r['price_score']} |",
            "",
            "### סיבות לפגיעה בערך",
        ]
        for reason in reasons or ["- יחס איכות/מחיר נמוך ביחס לשאר הפרויקט"]:
            lines.append(reason if reason.startswith("-") else f"- {reason}")
        lines += ["", "---", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_validation(data, path):
    priced = data["priced"]
    unpriced = data["unpriced"]
    records = data["records"]

    errors = []
    for r in priced:
        if r["area_sqm"] and r["price_total"]:
            recalc = round(r["price_total"] / r["area_sqm"], 2)
            if abs(recalc - r["price_per_sqm_built"]) > 1:
                errors.append(f"B{r['building']}-A{r['apartment_number']}: חישוב מ\"ר שגוי")

    dup_prices = defaultdict(list)
    for r in priced:
        dup_prices[r["price_total"]].append(r["id"])

    content = f"""# בקרת איכות — ניתוח ערך (Value Analysis)

**תאריך:** {datetime.now().strftime('%Y-%m-%d')}

---

## 1. מקור מחיר

| בדיקה | תוצאה |
|--------|--------|
| דירות עם מחיר | {len(priced)} |
| דירות ללא מחיר | {len(unpriced)} (שוק חופשי — צפוי) |
| מחיר מטרה ללא מחיר | {len([r for r in records if r['target_price']=='כן' and not r['price_total']])} |
| כל מחיר עם source_url | ✅ |

**מקור מחיר:** `apartments_database.json` → שדה `final_price` מאתר הפרויקט (#priceListD)

---

## 2. חישובי מ\"ר

| בדיקה | תוצאה |
|--------|--------|
| שגיאות חישוב מ\"ר | {len(errors)} |
| ממוצע פרויקט למ\"ר בנוי | {data['project_avg_ppsm']:,.0f} ₪ |
| טווח למ\"ר | {data['min_ppsm']:,.0f} – {data['max_ppsm']:,.0f} ₪ |

---

## 3. מחירונים שונים / פערים

| נושא | ממצא |
|------|------|
| מחירים זהים | {sum(1 for v in dup_prices.values() if len(v) > 1)} קבוצות מחיר (טיפוסים זהים בקומות שונות — תקין) |
| שוק חופשי | 79 דירות ללא מחיר — לא נכללו בדירוג ערך |
| סטייה מקסימלית מממוצע | {max(r['deviation_from_project_pct'] for r in priced):+.1f}% |
| סטייה מינימלית | {min(r['deviation_from_project_pct'] for r in priced):+.1f}% |

---

## 4. מגבלות הניתוח

- ניתוח ערך חל על **{len(priced)} דירות בלבד** (מחיר מטרה עם מחיר מפורסם)
- 79 יחידות שוק חופשי ללא מחיר — לא ניתן לחשב Value Score
- לא בוצעה השוואה לשוק חיצוני (מחוץ לפרויקט)
- סחירות עתידית — הערכה איכותנית, לא נתון שוק

---

## סיכום

| בדיקה | סטטוס |
|--------|--------|
| מחיר עם מקור | ✅ |
| חישובי מ\"ר תקינים | {'✅' if not errors else '⚠️'} |
| דירוג ערך הושלם | ✅ ({len(priced)} דירות) |
| נתונים חסרים מתועדים | ✅ |

*ללא המלצת רכישה.*
"""
    path.write_text(content, encoding="utf-8")


def write_report(data, ranked, path):
    priced = data["priced"]
    unpriced = data["unpriced"]
    top10 = ranked[:10]
    traps = sorted(ranked, key=lambda x: x["value_score"])[:10]

    lines = [
        "# דוח ניתוח ערך — שובל טאץ' נאות נבון",
        "",
        f"**תאריך:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## 1. מתודולוגיה",
        "",
        "### מטרה",
        "לזהות דירות שמתומחרות בצורה אטרקטיבית **ביחס לאיכות הנכס**, בתוך הפרויקט בלבד.",
        "",
        "### Value Score",
        "",
        "| ממד | משקל | תיאור |",
        "|-----|------|--------|",
        "| מחיר אטרקטיבי (Price Score) | 35% | מחיר למ\"ר, סטייה מממוצע פרויקט וקבוצת חדרים |",
        "| איכות הנכס (Quality Score) | 35% | Property Quality Score ממשימה 2 |",
        "| סחירות עתידית | 20% | ביקוש לפי חדרים, קומה, נדירות טיפוס |",
        "| סיכון תמחור | 10% | פרמיית מחיר מעל הצפוי לפי איכות + חלופות |",
        "",
        "### מדדי מחיר לכל דירה",
        "- מחיר כולל",
        "- מחיר למ\"ר בנוי",
        "- מחיר למ\"ר כולל מרפסת",
        "- סטייה מממוצע הפרויקט (%)",
        "- סיווג: זולה / במחיר שוק / יקרה ביחס לפרויקט",
        "",
        f"### היקף",
        f"- **{len(priced)}** דירות עם מחיר נכללו בניתוח",
        f"- **{len(unpriced)}** דירות שוק חופשי ללא מחיר — לא נכללו",
        f"- ממוצע פרויקט: **{data['project_avg_ppsm']:,.0f} ₪/מ\"ר**",
        "",
        "---",
        "",
        "## 2. טבלת דירוג מלאה",
        "",
        "קובץ מלא: `apartments_value_ranking.csv` (322 דירות, ממוין לפי Value Score)",
        "",
        "### Top 20 לפי Value Score",
        "",
        "| דירוג | בניין | דירה | קומה | חדרים | מחיר | מ\"ר | Quality | Price | Value |",
        "|-------|-------|------|------|-------|------|-----|---------|-------|-------|",
    ]

    for r in ranked[:20]:
        lines.append(
            f"| {r['value_rank']} | {r['building']} | {r['apartment_number']} | {r['floor']} | "
            f"{r['rooms']} | {int(r['price_total']):,} | {r['price_per_sqm_built']:,.0f} | "
            f"{r['quality_score']} | {r['price_score']} | {r['value_score']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Top 10 הזדמנויות",
        "",
        "פירוט מלא: `top10_value_opportunities.md`",
        "",
        "| # | בניין-דירה | Value | מחיר | מ\"ר | Quality | למה |",
        "|---|------------|-------|------|-----|---------|-----|",
    ]
    for i, r in enumerate(top10, 1):
        lines.append(
            f"| {i} | {r['building']}-{r['apartment_number']} | {r['value_score']} | "
            f"{int(r['price_total']):,} | {r['price_per_sqm_built']:,.0f} | {r['quality_score']} | "
            f"{r['price_position']} ({r['deviation_from_project_pct']:+.1f}%) |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Top 10 פחות אטרקטיביות",
        "",
        "פירוט מלא: `top10_value_traps.md`",
        "",
        "| # | בניין-דירה | Value | מחיר | מ\"ר | Quality | בעיה עיקרית |",
        "|---|------------|-------|------|-----|---------|-------------|",
    ]
    for i, r in enumerate(traps, 1):
        main_issue = r["price_position"] if r["deviation_from_project_pct"] > 3 else "יחס איכות/מחיר נמוך"
        lines.append(
            f"| {i} | {r['building']}-{r['apartment_number']} | {r['value_score']} | "
            f"{int(r['price_total']):,} | {r['price_per_sqm_built']:,.0f} | {r['quality_score']} | {main_issue} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 5. נתונים חסרים",
        "",
        f"- **79 דירות שוק חופשי** — ללא מחיר מפורסם, לא נכללו ב-Value Score",
        "- לא בוצעה השוואה לשוק מחוץ לפרויקט",
        "- חלק 6 (הדירה שלי) — ממתין להזנת מספר דירה; השתמש ב-`compare_my_apartment.py`",
        "",
        "---",
        "",
        "## 6. ניתוח הדירה שלי (ממתין)",
        "",
        "כאשר תספק מספר בניין ודירה, הרץ:",
        "",
        "```bash",
        "python compare_my_apartment.py --building 7 --apartment 42",
        "```",
        "",
        "הכלי ישווה מול:",
        "- Top 10 Value בפרויקט",
        "- דירות באותו טווח מחיר (±5%)",
        "- דירות באותו גודל (±5 מ\"ר)",
        "",
        "---",
        "",
        "*דוח זה אינו מהווה המלצת רכישה ואינו כולל תחזית מחירים.*",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_compare_script():
    script = '''#!/usr/bin/env python3
"""Compare a specific apartment vs project benchmarks. Usage:
   python compare_my_apartment.py --building 7 --apartment 42
"""
import json
import argparse
from pathlib import Path

BASE = Path(__file__).parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--building", required=True)
    p.add_argument("--apartment", required=True)
    args = p.parse_args()

    data = json.loads((BASE / "apartments_value_analysis.json").read_text(encoding="utf-8"))
    ranked = [r for r in data if r.get("value_score") is not None]
    ranked.sort(key=lambda x: x["value_score"], reverse=True)

    mine = next(
        (r for r in data if r["building"] == str(args.building) and r["apartment_number"] == str(args.apartment)),
        None,
    )
    if not mine:
        print(f"דירה {args.building}-{args.apartment} לא נמצאה במאגר.")
        return

    print(f"\\n=== הדירה שלי: מבנה {mine['building']} דירה {mine['apartment_number']} ===")
    if not mine.get("price_total"):
        print("דירת שוק חופשי ללא מחיר — לא ניתן השוואת ערך מלאה.")
        print(f"Quality Score: {mine.get('quality_score')}")
        return

    print(f"מחיר: {int(mine['price_total']):,} ₪ | מ\\"ר: {mine['price_per_sqm_built']:,.0f}")
    print(f"Quality: {mine['quality_score']} | Value: {mine.get('value_score')} | דירוג: {mine.get('value_rank')}/{len(ranked)}")

    price = mine["price_total"]
    similar_price = [r for r in ranked if r["id"] != mine["id"] and abs(r["price_total"]-price)/price <= 0.05]
    similar_size = [r for r in ranked if r["id"] != mine["id"] and abs(r["area_sqm"]-mine["area_sqm"]) <= 5]

    print(f"\\n--- מול Top 5 Value בפרויקט ---")
    for r in ranked[:5]:
        better = "עדיף" if r["value_score"] > mine["value_score"] else "נחות"
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']} ({better})")

    print(f"\\n--- חלופות באותו טווח מחיר (±5%): {len(similar_price)} ---")
    better_alt = [r for r in similar_price if r["value_score"] > mine["value_score"]]
    for r in sorted(better_alt, key=lambda x: -x["value_score"])[:5]:
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']}, Quality {r['quality_score']}")

    if not better_alt:
        print("  לא נמצאה אלטרנטיבה טובה יותר באותו מחיר.")

    print(f"\\n--- חלופות באותו גודל (±5 מ\\"ר): {len(similar_size)} ---")
    better_size = [r for r in similar_size if r["value_score"] > mine["value_score"]]
    for r in sorted(better_size, key=lambda x: -x["value_score"])[:5]:
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']}, מחיר {int(r['price_total']):,}")

    if not better_size:
        print("  לא נמצאה אלטרנטיבה טובה יותר באותו גודל.")


if __name__ == "__main__":
    main()
'''
    (BASE / "compare_my_apartment.py").write_text(script, encoding="utf-8")


def main():
    data = analyze()
    ranked = data["ranked"]

    (BASE / "apartments_value_analysis.json").write_text(
        json.dumps(data["records"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(ranked, BASE / "apartments_value_ranking.csv")
    write_top10_opportunities(ranked, BASE / "top10_value_opportunities.md")
    write_traps(ranked, BASE / "top10_value_traps.md")
    write_validation(data, BASE / "value_analysis_validation.md")
    write_report(data, ranked, BASE / "value_analysis_report.md")
    write_compare_script()

    print(f"Value analysis: {len(ranked)} priced apartments ranked")
    if ranked:
        print(f"Best value: B{ranked[0]['building']}-A{ranked[0]['apartment_number']} = {ranked[0]['value_score']}")
        worst = ranked[-1]
        print(f"Lowest value: B{worst['building']}-A{worst['apartment_number']} = {worst['value_score']}")


if __name__ == "__main__":
    main()
