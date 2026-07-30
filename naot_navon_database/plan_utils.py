"""Shared utilities for apartment plan linking, caching, and deduplication."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).parent
PDFS_JSON = BASE / "04_documents" / "pdfs.json"
APARTMENTS_JSON = BASE / "02_apartments" / "apartments.json"
APARTMENTS_DB_JSON = BASE / "apartments_database.json"
PLANS_CACHE_DIR = BASE / "04_documents" / "plans_cache"


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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_plan_indexes(pdfs: list[dict]) -> tuple[dict, dict]:
    """Return (apartment_plans, floor_plans) keyed by building -> apt/floor -> url."""
    apartment_plans: dict[str, dict[str, str]] = defaultdict(dict)
    floor_plans: dict[str, dict[str, str]] = defaultdict(dict)

    for pdf in pdfs:
        category = pdf.get("category")
        building = str(pdf.get("building", ""))
        url = pdf.get("url") or pdf.get("decoded_url")
        if not building or not url:
            continue

        match = re.search(r"/(\d+)\.pdf", url)
        if not match:
            continue
        file_num = match.group(1)

        if category == "apartment_plan":
            apartment_plans[building][file_num] = url
        elif category == "floor_plan":
            floor_plans[building][file_num] = url

    return dict(apartment_plans), dict(floor_plans)


def link_apartment_plans(apartments: list[dict], pdfs: list[dict] | None = None) -> dict:
    """Fill apartment_plan_url and floor_plan_url on each apartment record."""
    if pdfs is None:
        pdfs = load_json(PDFS_JSON)

    apartment_plans, floor_plans = build_plan_indexes(pdfs)

    stats = {
        "total": len(apartments),
        "apartment_plan_linked": 0,
        "floor_plan_linked": 0,
        "target_with_plan": 0,
        "target_without_plan": 0,
        "free_market_without_plan": 0,
        "missing_floor_plan": 0,
    }

    for apt in apartments:
        building = str(apt.get("building", ""))
        apt_num = str(apt.get("apartment_number", ""))
        floor_num = floor_numeric(apt.get("floor", ""))

        apt_url = apartment_plans.get(building, {}).get(apt_num)
        floor_url = floor_plans.get(building, {}).get(str(floor_num))

        apt["apartment_plan_url"] = apt_url
        apt["floor_plan_url"] = floor_url

        if apt_url:
            stats["apartment_plan_linked"] += 1
            if apt.get("target_price") == "כן":
                stats["target_with_plan"] += 1
            else:
                stats["free_market_without_plan"] += 1
        elif apt.get("target_price") == "כן":
            stats["target_without_plan"] += 1
        else:
            stats["free_market_without_plan"] += 1

        if floor_url:
            stats["floor_plan_linked"] += 1
        elif apt_url:
            stats["missing_floor_plan"] += 1

    return stats


def dedup_fingerprint(apt: dict) -> tuple:
    """Group key for plan analysis deduplication."""
    return (apt.get("apartment_type"), apt.get("directions"))


def get_dedup_representatives(apartments: list[dict]) -> dict[tuple, dict]:
    """Pick one representative apartment per (type, directions) with a plan URL."""
    reps: dict[tuple, dict] = {}
    for apt in apartments:
        if apt.get("target_price") != "כן" or not apt.get("apartment_plan_url"):
            continue
        key = dedup_fingerprint(apt)
        if key not in reps:
            reps[key] = apt
    return reps


def cache_path_for(apt: dict) -> Path:
    return PLANS_CACHE_DIR / f"{apt['id']}.pdf"


def download_plan(apt: dict, force: bool = False) -> Path | None:
    """Download apartment plan PDF to local cache. Returns path or None."""
    url = apt.get("apartment_plan_url")
    if not url:
        return None

    PLANS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = cache_path_for(apt)
    if dest.exists() and not force:
        return dest

    try:
        req = Request(url, headers={"User-Agent": "naot-navon-dashboard/1.0"})
        with urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return dest
    except Exception:
        return None


def render_pdf_first_page(pdf_path: Path, png_path: Path | None = None, dpi: int = 150) -> Path | None:
    """Render first page of PDF to PNG. Requires pymupdf."""
    try:
        import fitz  # pymupdf
    except ImportError:
        return None

    if png_path is None:
        png_path = pdf_path.with_suffix(".png")

    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=dpi)
        pix.save(str(png_path))
        doc.close()
        return png_path
    except Exception:
        return None
