#!/usr/bin/env python3
"""Compare a specific apartment vs project benchmarks. Usage:
   python compare_my_apartment.py --building 7 --apartment 42
"""
import json
import argparse
import sys
from pathlib import Path

BASE = Path(__file__).parent

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


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

    print(f"\n=== הדירה שלי: מבנה {mine['building']} דירה {mine['apartment_number']} ===")
    if not mine.get("price_total"):
        print("דירת שוק חופשי ללא מחיר — לא ניתן השוואת ערך מלאה.")
        print(f"Quality Score: {mine.get('quality_score')}")
        return

    print(f"מחיר: {int(mine['price_total']):,} ₪ | מ\"ר: {mine['price_per_sqm_built']:,.0f}")
    print(f"Quality: {mine['quality_score']} | Value: {mine.get('value_score')} | דירוג: {mine.get('value_rank')}/{len(ranked)}")

    price = mine["price_total"]
    similar_price = [r for r in ranked if r["id"] != mine["id"] and abs(r["price_total"]-price)/price <= 0.05]
    similar_size = [r for r in ranked if r["id"] != mine["id"] and abs(r["area_sqm"]-mine["area_sqm"]) <= 5]

    print(f"\n--- מול Top 5 Value בפרויקט ---")
    for r in ranked[:5]:
        better = "עדיף" if r["value_score"] > mine["value_score"] else "נחות"
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']} ({better})")

    print(f"\n--- חלופות באותו טווח מחיר (±5%): {len(similar_price)} ---")
    better_alt = [r for r in similar_price if r["value_score"] > mine["value_score"]]
    for r in sorted(better_alt, key=lambda x: -x["value_score"])[:5]:
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']}, Quality {r['quality_score']}")

    if not better_alt:
        print("  לא נמצאה אלטרנטיבה טובה יותר באותו מחיר.")

    print(f"\n--- חלופות באותו גודל (±5 מ\"ר): {len(similar_size)} ---")
    better_size = [r for r in similar_size if r["value_score"] > mine["value_score"]]
    for r in sorted(better_size, key=lambda x: -x["value_score"])[:5]:
        print(f"  B{r['building']}-A{r['apartment_number']}: Value {r['value_score']}, מחיר {int(r['price_total']):,}")

    if not better_size:
        print("  לא נמצאה אלטרנטיבה טובה יותר באותו גודל.")


if __name__ == "__main__":
    main()
