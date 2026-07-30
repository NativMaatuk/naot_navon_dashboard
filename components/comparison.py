import pandas as pd
import streamlit as st

from utils.formatters import format_price, format_number


COMPARE_FIELDS = [
    ("apartment_number", "דירה"),
    ("building", "בניין"),
    ("floor", "קומה"),
    ("rooms", "חדרים"),
    ("area_sqm", "שטח (מ\"ר)"),
    ("balcony_garden_sqm", "מרפסת (מ\"ר)"),
    ("price_total", "מחיר"),
    ("price_per_sqm_built", "מחיר למ\"ר"),
    ("view_classification", "נוף"),
    ("quality_score", "Quality Score"),
    ("value_score", "Value Score"),
    ("premium_exit_score", "Premium Exit Score"),
]


def render_comparison(df: pd.DataFrame):
    st.header("השוואת דירות")
    st.caption("בחר 2–5 דירות להשוואה")

    labels = df["label"].tolist()
    selected = st.multiselect("דירות להשוואה", labels, max_selections=5)

    if len(selected) < 2:
        st.info("בחר לפחות 2 דירות.")
        return

    subset = df[df["label"].isin(selected)].set_index("label")

    rows = []
    for field, label in COMPARE_FIELDS:
        if field not in subset.columns:
            continue
        row = {"מאפיין": label}
        for lbl in selected:
            val = subset.loc[lbl, field]
            if field == "price_total":
                row[lbl] = format_price(val)
            elif field in ("area_sqm", "balcony_garden_sqm", "quality_score", "value_score", "price_per_sqm_built"):
                row[lbl] = format_number(val, 1 if field in ("area_sqm", "balcony_garden_sqm") else 0)
            else:
                row[lbl] = val if pd.notna(val) else "—"
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
