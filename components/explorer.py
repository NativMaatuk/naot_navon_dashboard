import pandas as pd
import streamlit as st

from utils.formatters import format_price


EXPLORER_COLUMNS = [
    ("apartment_number", "מספר דירה"),
    ("building", "בניין"),
    ("floor", "קומה"),
    ("rooms", "חדרים"),
    ("area_sqm", "שטח"),
    ("balcony_garden_sqm", "מרפסת"),
    ("price_total", "מחיר"),
    ("price_per_sqm_built", "מחיר למ\"ר"),
    ("view_classification", "נוף"),
    ("quality_score", "Quality Score"),
    ("value_score", "Value Score"),
    ("premium_exit_score", "Premium Exit"),
]


def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("סינון")
    f1, f2, f3 = st.columns(3)
    f4, f5, f6 = st.columns(3)

    priced = df[df["has_price"]]
    min_p = int(priced["price_total"].min()) if not priced.empty else 0
    max_p = int(priced["price_total"].max()) if not priced.empty else 3_000_000

    with f1:
        price_range = st.slider("טווח מחיר (₪)", min_p, max_p, (min_p, max_p), step=50_000)
    with f2:
        rooms_opts = sorted(df["rooms_num"].dropna().unique())
        rooms_sel = st.multiselect("מספר חדרים", rooms_opts, default=list(rooms_opts))
    with f3:
        buildings = sorted(df["building_num"].dropna().unique())
        b_sel = st.multiselect("בניין", buildings, default=list(buildings))

    with f4:
        floors = sorted(df["floor"].dropna().unique(), key=lambda x: str(x))
        floor_sel = st.multiselect("קומה", floors, default=floors)
    with f5:
        views = sorted(df["view_classification"].dropna().unique()) if "view_classification" in df.columns else []
        view_sel = st.multiselect("נוף", views, default=views) if views else []
    with f6:
        q_min, q_max = st.slider(
            "ציון איכות",
            float(df["quality_score"].min()) if df["quality_score"].notna().any() else 0,
            float(df["quality_score"].max()) if df["quality_score"].notna().any() else 100,
            (0.0, 100.0),
        )

    v_min, v_max = st.slider("ציון Value", 0.0, 100.0, (0.0, 100.0))
    pe_min, pe_max = st.slider("Premium Exit Score", 0.0, 100.0, (0.0, 100.0))

    out = df.copy()
    if rooms_sel:
        out = out[out["rooms_num"].isin(rooms_sel)]
    if b_sel:
        out = out[out["building_num"].isin(b_sel)]
    if floor_sel:
        out = out[out["floor"].isin(floor_sel)]
    if view_sel and "view_classification" in out.columns:
        out = out[out["view_classification"].isin(view_sel)]
    if out["quality_score"].notna().any():
        out = out[(out["quality_score"].fillna(0) >= q_min) & (out["quality_score"].fillna(0) <= q_max)]
    if out["value_score"].notna().any():
        out = out[(out["value_score"].fillna(0) >= v_min) | (out["value_score"].isna())]
        out = out[(out["value_score"].fillna(0) <= v_max) | (out["value_score"].isna())]
    if "premium_exit_score" in out.columns:
        out = out[
            (out["premium_exit_score"].fillna(0) >= pe_min)
            & (out["premium_exit_score"].fillna(0) <= pe_max)
        ]

    out = out[(out["price_total"].fillna(0) >= price_range[0]) | (out["price_total"].isna())]
    out = out[(out["price_total"].fillna(max_p + 1) <= price_range[1]) | (out["price_total"].isna())]

    return out


def render_explorer(df: pd.DataFrame):
    st.header("חוקר דירות")
    filtered = _apply_filters(df)
    st.caption(f"מציג {len(filtered)} מתוך {len(df)} דירות")

    display = filtered.copy()
    display["מחיר"] = display["price_total"].apply(format_price)
    display["מחיר למ\"ר"] = display["price_per_sqm_built"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "—"
    )

    cols = [c[0] for c in EXPLORER_COLUMNS]
    labels = {c[0]: c[1] for c in EXPLORER_COLUMNS}
    show = display[[c for c in cols if c in display.columns]].rename(columns=labels)

    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Quality Score": st.column_config.NumberColumn(format="%.1f"),
            "Value Score": st.column_config.NumberColumn(format="%.1f"),
            "שטח": st.column_config.NumberColumn(format="%.1f"),
            "מרפסת": st.column_config.NumberColumn(format="%.1f"),
        },
    )
