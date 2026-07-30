"""Shared chart components."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.floor import floor_numeric


def render_analytics_charts(df: pd.DataFrame):
    priced = df[df["has_price"]].copy()
    if priced.empty:
        st.info("אין דירות עם מחיר להצגת גרפים.")
        return

    st.subheader("גרפים אנליטיים")

    c1, c2 = st.columns(2)

    with c1:
        floor_df = priced.copy()
        floor_df["floor_num"] = floor_df["floor"].apply(floor_numeric)
        agg = floor_df.groupby("floor_num", as_index=False)["price_per_sqm_built"].mean()
        fig = px.line(
            agg, x="floor_num", y="price_per_sqm_built",
            title="מחיר ממוצע למ\"ר לפי קומה",
            labels={"floor_num": "קומה", "price_per_sqm_built": "₪/מ\"ר"},
            markers=True,
        )
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.histogram(
            priced, x="price_total", nbins=30,
            title="התפלגות מחירים",
            labels={"price_total": "מחיר (₪)"},
        )
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        scatter = priced.dropna(subset=["quality_score", "price_per_sqm_built"])
        if not scatter.empty:
            fig = px.scatter(
                scatter, x="price_per_sqm_built", y="quality_score",
                hover_data=["building", "apartment_number", "floor"],
                title="Quality Score מול מחיר למ\"ר",
                labels={"price_per_sqm_built": "₪/מ\"ר", "quality_score": "Quality Score"},
                opacity=0.7,
            )
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        scatter_v = priced.dropna(subset=["value_score", "price_total"])
        if not scatter_v.empty:
            fig = px.scatter(
                scatter_v, x="price_total", y="value_score",
                hover_data=["building", "apartment_number"],
                title="Value Score מול מחיר",
                labels={"price_total": "מחיר (₪)", "value_score": "Value Score"},
                opacity=0.7,
            )
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    top_priced = priced.nsmallest(40, "price_per_sqm_built").copy()
    top_priced["apt_label"] = top_priced.apply(
        lambda r: f"B{r['building']}-A{r['apartment_number']}", axis=1
    )
    fig = px.bar(
        top_priced, x="apt_label", y="price_per_sqm_built",
        title="40 הדירות עם מחיר למ\"ר הנמוך ביותר",
        labels={"apt_label": "דירה", "price_per_sqm_built": "₪/מ\"ר"},
    )
    fig.update_layout(height=400, xaxis_tickangle=-45, margin=dict(l=20, r=20, t=40, b=80))
    st.plotly_chart(fig, use_container_width=True)
