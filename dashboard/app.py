"""Entry point for the Market Data Dashboard"""

import streamlit as st

from config import APP_TITLE, ENVIRONMENT, get_available_views, render_view_selector
from views.market import render_market_dashboard_view
from views.warehouse import render_warehouse_explorer


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title(f"📊 {APP_TITLE}")
    st.markdown(f"**Environment**: `{ENVIRONMENT}`")

    available_views = get_available_views()
    selected_view = render_view_selector(st.sidebar, available_views)

    def _render_warehouse_fallback():
        render_warehouse_explorer(key_prefix="warehouse_fallback", show_header=False)

    if selected_view == "market":
        render_market_dashboard_view(
            st.sidebar,
            on_empty_view=_render_warehouse_fallback,
        )
    elif selected_view == "warehouse":
        render_warehouse_explorer(key_prefix="warehouse_main", show_header=True)
    else:
        st.error(
            "Selected view is not available. Please update dashboard configuration."
        )


if __name__ == "__main__":
    main()
