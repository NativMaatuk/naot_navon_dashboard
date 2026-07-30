import pandas as pd
import plotly.express as px
import streamlit as st

from utils.floor import floor_numeric


def render_overview(df: pd.DataFrame, project: dict):
    st.header("סקירת פרויקט")
    st.caption("שובל טאץ' — נאות נבון חיפה")

    priced = df[df["has_price"]]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("דירות", len(df))
    c2.metric("בניינים", df["building"].nunique())
    if not priced.empty:
        c3.metric("מחיר מינימום", f"{int(priced['price_total'].min()):,} ₪")
        c4.metric("מחיר מקסימום", f"{int(priced['price_total'].max()):,} ₪")
        c5.metric("מחיר ממוצע", f"{int(priced['price_total'].mean()):,} ₪")
        c6.metric("ממוצע למ\"ר", f"{int(priced['price_per_sqm_built'].mean()):,} ₪")
    else:
        for col in (c3, c4, c5, c6):
            col.metric("מחיר", "—")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        room_counts = df["rooms"].value_counts().sort_index()
        fig = px.bar(
            x=room_counts.index.astype(str), y=room_counts.values,
            title="התפלגות חדרים",
            labels={"x": "חדרים", "y": "מספר דירות"},
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        floor_df = df.copy()
        floor_df["floor_num"] = floor_df["floor"].apply(floor_numeric)
        floor_order = sorted(df["floor"].unique(), key=lambda f: floor_numeric(f))
        floor_counts = df["floor"].value_counts().reindex(floor_order).dropna()
        fig = px.bar(
            x=floor_counts.index.astype(str), y=floor_counts.values,
            title="התפלגות קומות",
            labels={"x": "קומה", "y": "מספר דירות"},
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    if project:
        with st.expander("פרטי פרויקט"):
            st.write(f"**יזם:** {project.get('developer', '—')}")
            st.write(f"**תוכנית:** {project.get('program', '—')}")
            st.write(f"**מיקום:** {project.get('location', '—')}")
            st.write(f"**מסירה:** {project.get('delivery_date', '—')}")
            st.write(f"**מחיר מטרה / שוק חופשי:** {project.get('target_price_units', '—')} / {project.get('free_market_units', '—')}")
            source_url = project.get("source_url")
            if source_url:
                st.markdown(f"**אתר הפרויקט:** [{source_url}]({source_url})")

    if "score_interior" in df.columns:
        with st.expander("ניתוח אדריכלי (תכניות דירה)"):
            analyzed = int(df["score_interior"].notna().sum())
            with_plan = int(df["apartment_plan_url"].notna().sum()) if "apartment_plan_url" in df.columns else 0
            a1, a2, a3 = st.columns(3)
            a1.metric("דירות עם ניתוח אדריכלי", analyzed)
            a2.metric("דירות עם תכנית PDF", with_plan)
            if analyzed:
                a3.metric("ציון תכנון פנים ממוצע", f"{df['score_interior'].mean():.1f}")
            else:
                a3.metric("ציון תכנון פנים ממוצע", "—")
            st.caption(
                "הניתוח מבוסס תכניות הדירה של דירות מחיר מטרה. "
                "פירוט מלא לכל דירה במסך \"חוקר דירות\"."
            )
