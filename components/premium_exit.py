import pandas as pd
import streamlit as st

from utils.formatters import format_price, format_number


def render_premium_exit(df: pd.DataFrame):
    st.header("Premium Exit Score")
    st.caption(
        "דירוג פוטנציאל ביקוש בשוק החופשי בעוד 5–10 שנים. "
        "ללא עדיפות אוטומטית למחיר נמוך."
    )

    with st.expander("מתודולוגיה"):
        st.markdown("""
| ממד | משקל |
|-----|------|
| נוף ופתיחות | 30% |
| קומה | 20% |
| נדירות בפרויקט | 20% |
| תכנון הדירה | 15% |
| מרפסת וחוץ | 10% |
| מחיר ביחס לפרויקט | 5% |

*מחיר — משקל נמוך בכוונה; מועדף תמחור מאוזן, לא בהכרח הזול ביותר.*
        """)

    ranked = df.sort_values("premium_exit_score", ascending=False).reset_index(drop=True)
    top_n = st.slider("מספר דירות בדירוג", 10, 30, 20)

    st.subheader(f"Top {top_n} — Premium Exit")

    for i, row in ranked.head(top_n).iterrows():
        rank = int(row["premium_exit_rank"]) if pd.notna(row.get("premium_exit_rank")) else i + 1
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**#{rank} — מבנה {row['building']} דירה {row['apartment_number']}** "
                    f"| {row.get('rooms')} חדרים | קומה {row['floor']}"
                )
                st.markdown("**למה הדירה דורגה גבוה:**")
                for reason in row.get("premium_exit_reasons") or []:
                    st.markdown(f"- {reason}")
            with c2:
                st.metric("Premium Exit", f"{row['premium_exit_score']:.1f}")
                st.caption(f"נוף {row.get('premium_view', 0):.0f} | קומה {row.get('premium_floor', 0):.0f}")
                if row.get("has_price"):
                    st.caption(format_price(row.get("price_total")))

    st.markdown("---")
    st.subheader("טבלת דירוג מלאה")

    show_cols = [
        "premium_exit_rank", "apartment_number", "building", "floor", "rooms",
        "premium_exit_score", "premium_view", "premium_floor", "premium_rarity",
        "premium_planning", "premium_outdoor", "premium_price",
        "view_classification", "price_total",
    ]
    labels = {
        "premium_exit_rank": "דירוג",
        "apartment_number": "דירה",
        "building": "בניין",
        "floor": "קומה",
        "rooms": "חדרים",
        "premium_exit_score": "Premium Exit",
        "premium_view": "נוף",
        "premium_floor": "קומה (ציון)",
        "premium_rarity": "נדירות",
        "premium_planning": "תכנון",
        "premium_outdoor": "חוץ",
        "premium_price": "מחיר (5%)",
        "view_classification": "סיווג נוף",
        "price_total": "מחיר",
    }
    table = ranked[[c for c in show_cols if c in ranked.columns]].rename(columns=labels)
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.subheader("פירוט דירה")
    options = ranked.head(top_n).apply(
        lambda r: f"#{int(r['premium_exit_rank'])} מבנה {r['building']} דירה {r['apartment_number']}", axis=1
    ).tolist()
    sel = st.selectbox("בחר דירה לפירוט", options)
    if sel:
        idx = options.index(sel)
        row = ranked.iloc[idx]
        st.markdown("**למה הדירה דורגה גבוה:**")
        for reason in row["premium_exit_reasons"]:
            st.write(f"- {reason}")
        st.markdown("**פירוט ציוני משנה:**")
        dims = [
            ("נוף ופתיחות (30%)", row["premium_view"]),
            ("קומה (20%)", row["premium_floor"]),
            ("נדירות (20%)", row["premium_rarity"]),
            ("תכנון (15%)", row["premium_planning"]),
            ("מרפסת וחוץ (10%)", row["premium_outdoor"]),
            ("מחיר בפרויקט (5%)", row["premium_price"]),
        ]
        for label, val in dims:
            st.write(f"- {label}: **{val:.1f}**")
        st.write(f"מרפסת/גינה: {format_number(row.get('balcony_garden_sqm'), 1)} מ\"ר")
        st.write(f"נוף: {row.get('view_classification', '—')}")
