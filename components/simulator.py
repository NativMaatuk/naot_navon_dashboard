import pandas as pd
import streamlit as st

from utils.formatters import format_price, format_number


def render_simulator(df: pd.DataFrame):
    st.header("סימולטור תקציב")
    st.caption("מצא דירות שמתאימות לתקציב הרכישה שלך")

    priced = df[df["has_price"]].copy()
    if priced.empty:
        st.warning("אין דירות עם מחיר במאגר.")
        return

    min_b = int(priced["price_total"].min())
    max_b = int(priced["price_total"].max())
    default = min(1_800_000, max_b)

    budget = st.number_input(
        "תקציב רכישה (₪)", min_value=min_b, max_value=max_b,
        value=default, step=50_000,
    )

    tolerance = st.slider("גמישות תקציב (%)", 0, 15, 0) / 100
    max_price = budget * (1 + tolerance)

    sort_by = st.selectbox(
        "מיון תוצאות",
        ["value_score", "quality_score", "price_per_sqm_built"],
        format_func=lambda x: {
            "value_score": "Value Score (גבוה ראשון)",
            "quality_score": "Quality Score (גבוה ראשון)",
            "price_per_sqm_built": "מחיר למ\"ר (נמוך ראשון)",
        }[x],
    )

    matches = priced[priced["price_total"] <= max_price].copy()
    if sort_by == "price_per_sqm_built":
        matches = matches.sort_values(sort_by, ascending=True)
    else:
        matches = matches.sort_values(sort_by, ascending=False, na_position="last")

    st.metric("דירות מתאימות", len(matches), f"עד {format_price(max_price)}")

    if matches.empty:
        st.warning("לא נמצאו דירות בטווח התקציב.")
        return

    best = matches.iloc[0]
    st.success(
        f"העסקה המדורגת הראשונה בתקציב: **מבנה {best['building']} דירה {best['apartment_number']}** — "
        f"{format_price(best['price_total'])} | Quality {format_number(best.get('quality_score'), 1)} | "
        f"Value {format_number(best.get('value_score'), 1)}"
    )

    show = matches.head(30)[[
        "apartment_number", "building", "floor", "rooms", "area_sqm",
        "price_total", "price_per_sqm_built", "quality_score", "value_score", "view_classification",
    ]].rename(columns={
        "apartment_number": "דירה", "building": "בניין", "floor": "קומה",
        "rooms": "חדרים", "area_sqm": "שטח", "price_total": "מחיר",
        "price_per_sqm_built": "מ\"ר", "quality_score": "Quality",
        "value_score": "Value", "view_classification": "נוף",
    })
    st.dataframe(show, use_container_width=True, hide_index=True)
