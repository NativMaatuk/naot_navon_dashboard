#!/usr/bin/env python3
"""Link apartment and floor plan URLs from pdfs.json to apartment records."""
from __future__ import annotations

import csv
from datetime import datetime

from plan_utils import (
    APARTMENTS_DB_JSON,
    APARTMENTS_JSON,
    BASE,
    link_apartment_plans,
    load_json,
    save_json,
)


def write_coverage_report(stats: dict) -> None:
    report = f"""# דוח כיסוי תכניות דירה

**תאריך:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

| מדד | ערך |
|-----|-----|
| סה"כ דירות | {stats['total']} |
| תכנית דירה מקושרת | {stats['apartment_plan_linked']} |
| תכנית קומה מקושרת | {stats['floor_plan_linked']} |
| מחיר מטרה עם תכנית | {stats['target_with_plan']} |
| מחיר מטרה ללא תכנית | {stats['target_without_plan']} |
| שוק חופשי ללא תכנית | {stats['free_market_without_plan']} |
| תכנית דירה ללא תכנית קומה | {stats['missing_floor_plan']} |
"""
    (BASE / "06_quality_check" / "plan_link_coverage.md").write_text(report, encoding="utf-8")
    print(
        f"Coverage: {stats['apartment_plan_linked']} apt plans, "
        f"{stats['floor_plan_linked']} floor plans, "
        f"{stats['target_with_plan']} target-price linked"
    )


def sync_apartments_database(apartments: list[dict]) -> None:
    save_json(APARTMENTS_DB_JSON, apartments)

    if apartments:
        fields = list(apartments[0].keys())
        csv_path = BASE / "apartments_database.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(apartments)


def main() -> dict:
    apartments = load_json(APARTMENTS_JSON)
    stats = link_apartment_plans(apartments)

    save_json(APARTMENTS_JSON, apartments)
    sync_apartments_database(apartments)
    write_coverage_report(stats)

    print(
        f"Linked plans: {stats['apartment_plan_linked']} apartment, "
        f"{stats['floor_plan_linked']} floor plans"
    )
    return stats


if __name__ == "__main__":
    main()
