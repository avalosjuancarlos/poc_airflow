"""Enhanced Data Export Component"""

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from config import EXCEL_SHEET_NAME, EXPORT_DATE_FORMAT
from icons import ICON_CSV, ICON_EXCEL, ICON_EXPORT, ICON_JSON, ICON_PARQUET


def export_to_csv(df: pd.DataFrame) -> bytes:
    """Export DataFrame to CSV"""
    return df.to_csv(index=False).encode("utf-8")


def export_to_excel(df: pd.DataFrame) -> bytes:
    """Export DataFrame to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET_NAME)
    return output.getvalue()


def export_to_json(df: pd.DataFrame) -> bytes:
    """Export DataFrame to JSON"""
    return df.to_json(orient="records", date_format="iso").encode("utf-8")


def export_to_parquet(df: pd.DataFrame) -> bytes:
    """Export DataFrame to Parquet"""
    output = BytesIO()
    df.to_parquet(output, index=False, engine="pyarrow")
    return output.getvalue()


def render_export_buttons(df: pd.DataFrame, ticker: str, prefix: str = ""):
    """Render export buttons for multiple formats"""
    if df.empty:
        st.warning("No data to export")
        return

    st.subheader(f"{ICON_EXPORT} Export Data")

    timestamp = datetime.now().strftime(EXPORT_DATE_FORMAT)
    base_filename = f"{ticker}_market_data_{timestamp}"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        csv_data = export_to_csv(df)
        st.download_button(
            label=f"{ICON_CSV} CSV",
            data=csv_data,
            file_name=f"{base_filename}.csv",
            mime="text/csv",
            key=f"{prefix}_export_csv",
        )

    with col2:
        try:
            excel_data = export_to_excel(df)
            st.download_button(
                label=f"{ICON_EXCEL} Excel",
                data=excel_data,
                file_name=f"{base_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{prefix}_export_excel",
            )
        except ImportError:
            st.info("Excel export requires openpyxl")

    with col3:
        json_data = export_to_json(df)
        st.download_button(
            label=f"{ICON_JSON} JSON",
            data=json_data,
            file_name=f"{base_filename}.json",
            mime="application/json",
            key=f"{prefix}_export_json",
        )

    with col4:
        try:
            parquet_data = export_to_parquet(df)
            st.download_button(
                label=f"{ICON_PARQUET} Parquet",
                data=parquet_data,
                file_name=f"{base_filename}.parquet",
                mime="application/octet-stream",
                key=f"{prefix}_export_parquet",
            )
        except ImportError:
            st.info("Parquet export requires pyarrow")

