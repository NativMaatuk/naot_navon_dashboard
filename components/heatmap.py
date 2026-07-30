import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.floor import floor_numeric


METRIC_OPTIONS = {
    "premium_exit_score": "Premium Exit Score",
    "quality_score": "איכות (Quality Score)",
    "price_total": "מחיר",
    "value_score": "Value Score",
    "price_per_sqm_built": "מחיר למ\"ר",
}


def render_heatmap(df: pd.DataFrame):
    st.header("מפת חום — בניין × קומה")
    st.caption("זיהוי ויזואלי של אזורים חזקים בפרויקט")

    metric = st.selectbox("מדד להצגה", list(METRIC_OPTIONS.keys()), format_func=lambda k: METRIC_OPTIONS[k])
    only_priced = st.checkbox("רק דירות עם מחיר", value=metric in ("price_total", "value_score", "price_per_sqm_built"))

    data = df.copy()
    if only_priced:
        data = data[data["has_price"]]
    data = data.dropna(subset=[metric]) if metric in data.columns else data

    if data.empty:
        st.warning("אין נתונים להצגה עבור המדד שנבחר.")
        return

    data["floor_num"] = data["floor"].apply(floor_numeric)

    pivot = data.pivot_table(
        index="floor_num", columns="building_num", values=metric, aggfunc="mean",
    )
    pivot = pivot.sort_index()

    # Build custom y labels for floors
    floor_labels = {}
    for fl in data["floor"].unique():
        floor_labels[floor_numeric(fl)] = str(fl)
    y_labels = [floor_labels.get(i, str(i)) for i in pivot.index]

    z = pivot.values
    text = np.where(np.isnan(z), "", np.round(z, 1).astype(str))

    fig = px.imshow(
        z,
        x=[str(int(c)) for c in pivot.columns],
        y=y_labels,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdYlGn" if metric != "price_total" else "Blues",
        labels=dict(x="בניין", y="קומה", color=METRIC_OPTIONS[metric]),
        title=f"ממוצע {METRIC_OPTIONS[metric]} לפי בניין וקומה",
    )
    fig.update_layout(height=600, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "כל תא מייצג ממוצע של הדירות באותו בניין וקומה. "
        "תאים ריקים = אין דירות בצומת זו."
    )
