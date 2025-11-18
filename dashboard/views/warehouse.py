from datetime import datetime, timedelta
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.export import render_export_buttons
from icons import ICON_CODE, ICON_COPY, ICON_QUERY, ICON_REFRESH, ICON_SHARE, ICON_WAREHOUSE
from data import (
    build_warehouse_query,
    load_distinct_values,
    load_table_columns,
    load_warehouse_tables,
    run_warehouse_query,
)


def _validate_custom_filter(filter_str: str) -> tuple[bool, str]:
    """Ensure user-provided filter stays read-only and safe."""
    if not filter_str or not filter_str.strip():
        return True, ""

    normalized = filter_str.strip().lower()
    if ";" in normalized or "--" in normalized or "/*" in normalized or "*/" in normalized:
        return False, "Semicolons or SQL comments are not allowed."

    disallowed_keywords = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "call",
        "create",
        "replace",
        "grant",
        "revoke",
        "commit",
        "rollback",
        "vacuum",
    }
    pattern = r"\b(" + "|".join(disallowed_keywords) + r")\b"
    if re.search(pattern, normalized):
        return False, "Only read-only filters are supported. DDL/DML statements are blocked."

    return True, ""


def render_warehouse_explorer(key_prefix="warehouse", show_header=True):
    if show_header:
        st.header(f"{ICON_WAREHOUSE} Warehouse Explorer")
        st.caption(
            "Browse any warehouse table, preview SQL, and export results for downstream use."
        )

    if st.button(f"{ICON_REFRESH} Refresh warehouse data", key=f"{key_prefix}_refresh_button"):
        st.cache_data.clear()
        st.rerun()

    tables = load_warehouse_tables()
    if not tables:
        st.info(
            "Warehouse metadata is not available yet. Ensure the warehouse service is "
            "running and tables are created."
        )
        return

    table_options = [f"{row['table_schema']}.{row['table_name']}" for row in tables]
    selected_table = st.selectbox(
        "Select table",
        options=table_options,
        index=0,
        key=f"{key_prefix}_table",
    )

    schema, table = selected_table.split(".", 1)
    column_metadata = load_table_columns(schema, table)
    column_names = [col["column_name"] for col in column_metadata]
    column_map = {name.lower(): name for name in column_names}
    ticker_column = column_map.get("ticker")
    date_column = column_map.get("date")

    st.caption(
        f"Showing live data from `{schema}`.`{table}` ({len(column_metadata)} columns)"
    )

    filter_cols = st.columns(3)
    ticker_filter = []
    if ticker_column:
        with filter_cols[0]:
            ticker_values = load_distinct_values(schema, table, ticker_column, limit=50)
            ticker_filter = st.multiselect(
                "Ticker filter",
                options=ticker_values,
                default=[],
                help="Filter by ticker if available",
                key=f"{key_prefix}_ticker_filter",
            )

    date_range = None
    if date_column:
        with filter_cols[1]:
            default_end = datetime.utcnow().date()
            default_start = default_end - timedelta(days=30)
            date_range = st.date_input(
                "Date range",
                value=(default_start, default_end),
                help="Applies when the table has a `date` column",
                key=f"{key_prefix}_date_range",
            )

    with filter_cols[2]:
        limit_rows = st.slider(
            "Row limit",
            min_value=100,
            max_value=5000,
            value=500,
            step=100,
            key=f"{key_prefix}_limit",
        )

    custom_filter = st.text_input(
        "Advanced filter (SQL)",
        value="",
        help="Read-only filters only (e.g., close > 150). No DDL/DML allowed.",
        key=f"{key_prefix}_custom_filter",
    )
    is_filter_valid, filter_error = _validate_custom_filter(custom_filter)
    if not is_filter_valid:
        st.error(filter_error)
        st.stop()

    query, params = build_warehouse_query(
        schema,
        table,
        column_metadata,
        ticker_column,
        date_column,
        ticker_filter,
        date_range,
        custom_filter,
        limit_rows,
    )

    st.markdown("**Generated SQL**")
    st.code(query, language="sql")
    if params:
        st.caption(f"Parameters: {params}")

    with st.spinner("Running query..."):
        warehouse_df = run_warehouse_query(query, params)

    if warehouse_df.empty:
        st.warning("Query returned no rows. Adjust filters and try again.")
        return

    metric_cols = st.columns(3)
    with metric_cols[0]:
        st.metric("Records Returned", f"{len(warehouse_df):,}")
    with metric_cols[1]:
        st.metric("Columns", len(warehouse_df.columns))
    with metric_cols[2]:
        if date_column and date_column in warehouse_df.columns:
            latest_value = warehouse_df[date_column].max()
            metric_value = (
                latest_value.strftime("%Y-%m-%d")
                if hasattr(latest_value, "strftime")
                else str(latest_value)
            )
            metric_label = "Latest Date"
        else:
            metric_value = (
                str(warehouse_df.iloc[0, 0]) if not warehouse_df.empty else "N/A"
            )
            metric_label = "First Column Snapshot"
        st.metric(metric_label, metric_value)

    left_viz, right_viz = st.columns(2)

    if date_column and date_column in warehouse_df.columns:
        date_series = pd.to_datetime(
            warehouse_df[date_column], errors="coerce"
        ).dropna()
        if not date_series.empty:
            date_counts = (
                date_series.dt.date.value_counts()
                .sort_index()
                .rename_axis("date")
                .reset_index(name="records")
            )
            with left_viz:
                st.plotly_chart(
                    go.Figure(
                        data=[
                            go.Bar(
                                x=date_counts["date"],
                                y=date_counts["records"],
                                marker_color="indigo",
                            )
                        ],
                        layout=go.Layout(
                            title="Records by Date",
                            xaxis_title="Date",
                            yaxis_title="Records",
                        ),
                    ),
                    use_container_width=True,
                )

    if ticker_column and ticker_column in warehouse_df.columns:
        ticker_counts = (
            warehouse_df[ticker_column]
            .value_counts()
            .rename_axis("ticker")
            .reset_index(name="records")
        )
        with right_viz:
            st.plotly_chart(
                go.Figure(
                    data=[
                        go.Bar(
                            x=ticker_counts["ticker"],
                            y=ticker_counts["records"],
                            marker_color="teal",
                        )
                    ],
                    layout=go.Layout(
                        title="Records by Ticker",
                        xaxis_title="Ticker",
                        yaxis_title="Records",
                    ),
                ),
                use_container_width=True,
            )

    st.markdown("### Data Preview")
    st.dataframe(
        warehouse_df,
        use_container_width=True,
        height=500,
    )

    # Enhanced export with multiple formats
    export_name = f"{schema}_{table}"
    render_export_buttons(warehouse_df, export_name, prefix=f"{key_prefix}_warehouse")

    # Share query functionality
    st.markdown("---")
    st.subheader(f"{ICON_SHARE} Share Query")
    
    share_col1, share_col2 = st.columns(2)
    
    with share_col1:
        st.markdown(f"**{ICON_QUERY} Copy SQL Query**")
        st.code(query, language="sql")
        if st.button(f"{ICON_COPY} Copy SQL", key=f"{key_prefix}_copy_sql"):
            st.success("SQL query copied! (Use Ctrl+C / Cmd+C)")
    
    with share_col2:
        st.markdown("**Query Parameters**")
        if params:
            params_str = " | ".join([f"{k}={v}" for k, v in params.items()])
            st.code(params_str, language="text")
        else:
            st.info("No parameters for this query")
        
        # Generate shareable query code
        query_code = f"""
# Warehouse Query
# Table: {schema}.{table}
# Filters: {len(ticker_filter)} tickers, date range: {date_range}, limit: {limit_rows}

query = """
        query_code += f'"""{query}"""'
        query_code += f"\nparams = {params}"
        
        st.markdown(f"**{ICON_CODE} Python Code**")
        st.code(query_code, language="python")
        if st.button(f"{ICON_COPY} Copy Code", key=f"{key_prefix}_copy_code"):
            st.success("Python code copied!")

    with st.expander("Table schema"):
        if column_metadata:
            schema_df = pd.DataFrame(column_metadata)[
                ["column_name", "data_type", "is_nullable"]
            ]
            st.dataframe(schema_df, use_container_width=True)
        else:
            st.text("No metadata available.")

