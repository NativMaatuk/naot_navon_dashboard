import pandas as pd
import streamlit as st

from utils.formatters import format_price, format_number


RANK_MODES = {
    "premium_exit_score": "Premium Exit Score",
    "value_score": "Value Score",
    "quality_score": "Quality Score",
    "price_per_sqm_built": "מחיר למ\"ר (נמוך → גבוה)",
}


def _pros_cons(row: pd.Series) -> tuple[list[str], list[str]]:
    pros, cons = [], []
    if pd.notna(row.get("quality_score")) and row["quality_score"] >= 75:
        pros.append(f"איכות גבוהה ({row['quality_score']:.1f})")
    if pd.notna(row.get("value_score")) and row["value_score"] >= 75:
        pros.append(f"Value Score גבוה ({row['value_score']:.1f})")
    if pd.notna(row.get("deviation_from_project_pct")) and row["deviation_from_project_pct"] < -3:
        pros.append(f"מחיר למ\"ר מתחת לממוצע ({row['deviation_from_project_pct']:+.1f}%)")
    if pd.notna(row.get("score_view")) and row["score_view"] >= 75:
        pros.append("נוף / כיווני אוויר מוערכים")
    if pd.notna(row.get("score_interior")) and row["score_interior"] >= 75:
        pros.append(f"תכנון פנים טוב ({row['score_interior']:.1f})")

    if pd.notna(row.get("deviation_from_project_pct")) and row["deviation_from_project_pct"] > 5:
        cons.append(f"מחיר למ\"ר מעל ממוצע הפרויקט ({row['deviation_from_project_pct']:+.1f}%)")
    if pd.notna(row.get("quality_score")) and row["quality_score"] < 60:
        cons.append(f"איכות נמוכה יחסית ({row['quality_score']:.1f})")
    if not row.get("has_price"):
        cons.append("ללא מחיר מפורסם (שוק חופשי)")
    if pd.notna(row.get("pricing_risk")) and row["pricing_risk"] > 60:
        cons.append(f"סיכון תמחור מוערך ({row['pricing_risk']:.1f})")

    if not pros:
        pros.append("אין יתרון בולט בנתונים")
    if not cons:
        cons.append("אין חיסרון בולט בנתונים")
    return pros, cons


def render_ranking(df: pd.DataFrame):
    st.header("דירוג דירות")
    mode = st.radio("דירוג לפי", list(RANK_MODES.keys()), format_func=lambda k: RANK_MODES[k], horizontal=True)

    ranked = df.copy()
    if mode == "price_per_sqm_built":
        ranked = ranked[ranked["has_price"]].sort_values(mode, ascending=True)
    else:
        ranked = ranked.dropna(subset=[mode]).sort_values(mode, ascending=False)

    top20 = ranked.head(20)
    display_cols = ["apartment_number", "building", "floor", "rooms", "area_sqm",
                    "price_total", "price_per_sqm_built", "quality_score", "value_score",
                    "premium_exit_score"]
    labels = {
        "apartment_number": "דירה", "building": "בניין", "floor": "קומה",
        "rooms": "חדרים", "area_sqm": "שטח", "price_total": "מחיר",
        "price_per_sqm_built": "מ\"ר", "quality_score": "Quality", "value_score": "Value",
        "premium_exit_score": "Premium Exit",
    }
    show = top20[[c for c in display_cols if c in top20.columns]].rename(columns=labels)
    st.dataframe(show, use_container_width=True, hide_index=True)

    if mode == "premium_exit_score":
        st.subheader("למה הדירות דורגו גבוה")
        for _, row in top20.head(10).iterrows():
            st.markdown(f"**מבנה {row['building']} דירה {row['apartment_number']}** (Premium Exit: {row['premium_exit_score']:.1f})")
            for reason in row.get("premium_exit_reasons") or []:
                st.markdown(f"- {reason}")
            st.markdown("")

    st.subheader("פירוט דירה")
    options = top20.apply(lambda r: f"מבנה {r['building']} דירה {r['apartment_number']}", axis=1).tolist()
    sel = st.selectbox("בחר דירה", options)
    if sel:
        idx = options.index(sel)
        row = top20.iloc[idx]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**נתונים**")
            st.write(f"טיפוס: {row.get('apartment_type', '—')}")
            st.write(f"שטח: {format_number(row.get('area_sqm'), 1)} מ\"ר")
            st.write(f"מרפסת/גינה: {format_number(row.get('balcony_garden_sqm'), 1)} מ\"ר")
            st.write(f"מחיר: {format_price(row.get('price_total'))}")
            st.write(f"מחיר למ\"ר: {format_number(row.get('price_per_sqm_built'))} ₪")
            st.write(f"נוף: {row.get('view_classification', '—')}")
            st.write(f"כיוונים: {row.get('directions', '—')}")
        with c2:
            st.markdown("**ציונים**")
            st.write(f"Quality: {row.get('quality_score', '—')}")
            st.write(f"Value: {row.get('value_score', '—')}")
            st.write(f"Premium Exit: {row.get('premium_exit_score', '—')}")
            st.write(f"תכנון פנים: {format_number(row.get('score_interior'), 1) if pd.notna(row.get('score_interior')) else '—'}")
            st.write(f"נוף (מתכנית): {format_number(row.get('score_view_plan'), 1) if pd.notna(row.get('score_view_plan')) else '—'}")
            st.write(f"מיקום מחיר: {row.get('price_position', '—')}")

        plan_url = row.get("apartment_plan_url")
        if plan_url and pd.notna(plan_url):
            st.markdown(f"**תכנית דירה:** [{plan_url}]({plan_url})")
        floor_url = row.get("floor_plan_url")
        if floor_url and pd.notna(floor_url):
            st.markdown(f"**תכנית קומה:** [{floor_url}]({floor_url})")

        arch_notes = row.get("architecture_notes")
        if arch_notes and pd.notna(arch_notes):
            st.markdown("**ניתוח אדריכלי:**")
            st.write(arch_notes)
        elif not plan_url or pd.isna(plan_url):
            st.caption("אין ניתוח אדריכלי לדירה זו — תכנית דירה לא פורסמה באתר (דירת שוק חופשי).")

        if pd.notna(row.get("premium_exit_score")):
            st.markdown("**למה דורגה גבוה (Premium Exit):**")
            for reason in row.get("premium_exit_reasons") or []:
                st.write(f"- {reason}")

        pros, cons = _pros_cons(row)
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown("**יתרונות**")
            for p in pros:
                st.write(f"- {p}")
        with pc2:
            st.markdown("**חסרונות**")
            for c in cons:
                st.write(f"- {c}")

        st.markdown("**מקור:**")
        st.write(row.get("source_url", "—"))
