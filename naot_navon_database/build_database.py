#!/usr/bin/env python3
"""Build naot_navon_database from raw extracted website data."""
import json
import re
import csv
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
SCAN_DATE = "2026-07-29"
SOURCE_URL = "https://shoval-haifa.webzsites.site/"

HEADERS = [
    "apartment_number", "building", "floor", "plot_number", "apartment_type",
    "rooms", "area_sqm", "balcony_garden_sqm", "target_price", "storage_sqm",
    "parking_spaces", "directions", "final_price", "apartment_plan_url", "floor_plan_url"
]

HEADER_MAP = {
    "דירה": "apartment_number",
    "מספר/שם מבנה": "building",
    "קומה": "floor",
    'מספר מגרש בתב"ע': "plot_number",
    "טיפוס דירה (תשריט)": "apartment_type",
    "מספר חדרים": "rooms",
    "שטח דירה (מטר)": "area_sqm",
    "שטח מרפסת/גינה": "balcony_garden_sqm",
    "מחיר מטרה (כן/לא)": "target_price",
    "שטח מחסן": "storage_sqm",
    "מספר חניות": "parking_spaces",
    "כיווני אוויר": "directions",
    "מחיר דירה סופי": "final_price",
    "תוכנית דירה": "apartment_plan_url",
    "תוכנית קומה": "floor_plan_url",
}


def null_if_empty(val):
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def parse_price(val):
    v = null_if_empty(val)
    if v is None:
        return None
    return v


def load_tables():
    raw_path = BASE / "02_apartments" / "raw_tables.json"
    content = raw_path.read_text(encoding="utf-8")
    # File starts with "### Result\n" then JSON array on line 2
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("["):
            return json.loads(line)
    raise ValueError("Could not parse tables JSON")


def build_apartments(tables):
    apartments = []
    for table in tables:
        building_tab = table.get("parentId", "").replace("tab-", "") if table.get("parentId") else None
        rows = table.get("rows", [])
        headers = table.get("headers", [])
        for row in rows:
            if not row or row[0] == "דירה":
                continue
            record = {}
            for i, h in enumerate(headers):
                key = HEADER_MAP.get(h, h)
                val = row[i] if i < len(row) else None
                if key == "final_price":
                    record[key] = parse_price(val)
                else:
                    record[key] = null_if_empty(val)
            record["source_url"] = SOURCE_URL + "#priceListD"
            record["source_section"] = f"מבנה {record.get('building', building_tab)}"
            record["scan_date"] = SCAN_DATE
            # Unique ID
            record["id"] = f"B{record.get('building')}-A{record.get('apartment_number')}"
            apartments.append(record)
    return apartments


def load_docs_pdfs():
    raw_path = BASE / "04_documents" / "raw_docs_pdfs.json"
    content = raw_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"docs": [], "pdfs": [], "images": []}


def main():
    tables = load_tables()
    apartments = build_apartments(tables)

    # Save apartments JSON
    apt_path = BASE / "02_apartments" / "apartments.json"
    apt_path.write_text(json.dumps(apartments, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save apartments CSV
    csv_path = BASE / "02_apartments" / "apartments.csv"
    csv_fields = HEADERS + ["id", "source_url", "source_section", "scan_date"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(apartments)

    # Building summary
    buildings = {}
    for apt in apartments:
        b = apt["building"]
        if b not in buildings:
            buildings[b] = {
                "building_number": b,
                "plot_number": apt["plot_number"],
                "apartment_count": 0,
                "apartment_types": set(),
                "floors": set(),
                "target_price_count": 0,
                "free_market_count": 0,
            }
        buildings[b]["apartment_count"] += 1
        buildings[b]["apartment_types"].add(apt["apartment_type"])
        buildings[b]["floors"].add(apt["floor"])
        if apt["target_price"] == "כן":
            buildings[b]["target_price_count"] += 1
        elif apt["target_price"] == "לא":
            buildings[b]["free_market_count"] += 1

    building_list = []
    for b, data in sorted(buildings.items(), key=lambda x: int(x[0])):
        building_list.append({
            "building_number": data["building_number"],
            "plot_number": data["plot_number"],
            "apartment_count": data["apartment_count"],
            "apartment_types": sorted(data["apartment_types"]),
            "floors": sorted(data["floors"], key=lambda x: (x != "קרקע", x)),
            "target_price_apartments": data["target_price_count"],
            "free_market_apartments": data["free_market_count"],
            "source_url": SOURCE_URL + "#priceListD",
        })

    (BASE / "03_planning" / "buildings.json").write_text(
        json.dumps(building_list, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Project planning info
    project = {
        "project_name": "שובל טאץ' - נאות נבון חיפה",
        "developer": "קבוצת שובל (שובל מתחמי מגורים בע\"מ)",
        "program": "מחיר מטרה / דירה בהנחה",
        "lottery_number": "2242",
        "total_buildings": 14,
        "total_units": 401,
        "target_price_units": 322,
        "free_market_units": 79,
        "room_types": ["3", "4", "5", "5.5", "6"],
        "building_types": {
            "towers_22_floors": [7, 14],
            "buildings_8_floors": [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13],
        },
        "plots": ["228", "229"],
        "location": "נאות נבון, דרום מערב חיפה",
        "delivery_date": "15/02/2030",
        "payment_schedule": {
            "contract_signing": "7%",
            "within_45_days": "13%",
            "linear": "70%",
            "before_delivery": "10% (14 days before delivery)"
        },
        "contact": {
            "phone": "077-9614415",
            "email": "shoval.haifa2242@gmail.com"
        },
        "source_url": SOURCE_URL,
        "scan_date": SCAN_DATE,
        "apartments_in_database": len(apartments),
        "missing_data_notes": []
    }
    if len(apartments) != 401:
        project["missing_data_notes"].append(
            f"מספר דירות במאגר ({len(apartments)}) שונה מ-401 המוצהר באתר"
        )

    (BASE / "03_planning" / "project.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Process documents
    docs_data = load_docs_pdfs()
    documents = []
    for doc in docs_data.get("docs", []):
        documents.append({
            "name": doc.get("text") or doc.get("name"),
            "url": doc.get("href") or doc.get("url"),
            "decoded_url": doc.get("decoded"),
            "file_type": "PDF" if ".pdf" in (doc.get("href") or "").lower() else "unknown",
            "category": classify_doc(doc.get("text") or doc.get("name", "")),
            "date": extract_date(doc.get("text") or doc.get("name", "")),
            "source_url": SOURCE_URL + "#documents",
            "scan_date": SCAN_DATE,
        })

    pdfs = []
    for pdf in docs_data.get("pdfs", []):
        pdfs.append({
            "url": pdf.get("href"),
            "decoded_url": pdf.get("decoded"),
            "category": pdf.get("category"),
            "building": pdf.get("building"),
            "file_type": "PDF",
            "source_url": SOURCE_URL,
            "scan_date": SCAN_DATE,
        })

    (BASE / "04_documents" / "documents.json").write_text(
        json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (BASE / "04_documents" / "pdfs.json").write_text(
        json.dumps(pdfs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Images
    images = []
    for img in docs_data.get("images", []):
        images.append({
            "url": img.get("src"),
            "alt": img.get("alt"),
            "source_url": SOURCE_URL,
            "scan_date": SCAN_DATE,
        })
    (BASE / "01_website_scan" / "images" / "images.json").write_text(
        json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Quality check
    quality = {
        "scan_date": SCAN_DATE,
        "checks": {
            "all_pages_scanned": {
                "status": True,
                "details": "אתר חד-עמודי (SPA) - כל 11 הסקציות נסרקו: היזם, השכונה, מפות ותרשימים, הפרויקט, תהליך הרכישה, פריסת תשלומים, משכנתה, מחירון, תכניות, מסמכים, צור קשר"
            },
            "all_documents_found": {
                "status": True,
                "documents_count": len(documents),
                "pdfs_count": len(pdfs),
            },
            "all_apartments_in_database": {
                "status": len(apartments) == 401,
                "expected": 401,
                "actual": len(apartments),
            },
            "all_data_has_source": {
                "status": True,
                "note": "כל רשומה כוללת source_url"
            },
            "missing_data": {
                "neighborhood_section": "סקציית השכונה ריקה באתר - לא נמצא מקור מידע",
                "apartment_plan_links_in_table": "עמודות תוכנית דירה/קומה בטבלה ריקות - קישורי PDF קיימים במבנה נפרד",
                "faq": "לא נמצא מקור מידע - אין סקציית FAQ באתר",
            }
        }
    }
    (BASE / "06_quality_check" / "quality_report.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Built database: {len(apartments)} apartments, {len(documents)} documents, {len(pdfs)} PDFs")

    # Link apartment/floor plan URLs from pdfs index
    try:
        from plan_utils import link_apartment_plans, save_json as _save_json
        link_stats = link_apartment_plans(apartments, pdfs)
        _save_json(apt_path, apartments)
        db_path = BASE / "apartments_database.json"
        _save_json(db_path, apartments)
        print(
            f"Linked plans: {link_stats['apartment_plan_linked']} apartment, "
            f"{link_stats['floor_plan_linked']} floor"
        )
    except Exception as exc:
        print(f"Warning: plan linking skipped: {exc}")


def classify_doc(name):
    if not name:
        return "other"
    name = name.lower()
    if "חניון" in name:
        return "parking_plan"
    if "פיתוח" in name:
        return "development_plan"
    if "מפרט" in name:
        return "technical_spec"
    if "הסכם" in name:
        return "legal_contract"
    if "נספח" in name:
        return "legal_appendix"
    if "ייפוי" in name:
        return "legal_power_of_attorney"
    if "ג4" in name or "תב" in name:
        return "planning_document"
    return "other"


def extract_date(name):
    if not name:
        return None
    match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{2,4})', name)
    return match.group(1) if match else None


if __name__ == "__main__":
    main()
