"""Streamlit dashboard for Shoval Touch — Naot Navon project analysis."""
import streamlit as st

from data.loader import load_apartments, load_project
from components.overview import render_overview
from components.explorer import render_explorer
from components.heatmap import render_heatmap
from components.ranking import render_ranking
from components.comparison import render_comparison
from components.simulator import render_simulator
from components.charts import render_analytics_charts
from components.premium_exit import render_premium_exit

st.set_page_config(
    page_title="נאות נבון — Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "סקירה (Overview)": "overview",
    "חוקר דירות": "explorer",
    "מפת חום": "heatmap",
    "דירוג": "ranking",
    "Premium Exit": "premium_exit",
    "השוואת דירות": "comparison",
    "סימולטור תקציב": "simulator",
    "גרפים": "charts",
}


@st.cache_data(show_spinner="טוען נתונים...")
def get_data():
    return load_apartments(), load_project()


def main():
    st.sidebar.title("נאות נבון")
    st.sidebar.caption("שובל טאץ' — כלי חקירה וניתוח")
    page_label = st.sidebar.radio("ניווט", list(PAGES.keys()))
    page = PAGES[page_label]

    try:
        df, project = get_data()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.metric("דירות במאגר", len(df))
    st.sidebar.metric("עם מחיר", int(df["has_price"].sum()))
    st.sidebar.caption("מקור: apartments_database.json")

    if page == "overview":
        render_overview(df, project)
    elif page == "explorer":
        render_explorer(df)
    elif page == "heatmap":
        render_heatmap(df)
    elif page == "ranking":
        render_ranking(df)
    elif page == "premium_exit":
        render_premium_exit(df)
    elif page == "comparison":
        render_comparison(df)
    elif page == "simulator":
        render_simulator(df)
    elif page == "charts":
        st.header("גרפים אנליטיים")
        render_analytics_charts(df)

    st.sidebar.markdown("---")
    st.sidebar.caption("כלי חקירה בלבד — ללא המלצת השקעה")


if __name__ == "__main__":
    main()
