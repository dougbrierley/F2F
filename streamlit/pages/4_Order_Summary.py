import json
import re
import datetime
import boto3
import pandas as pd
from create_invoices import create_invoices
from datetime import datetime, timedelta
from openpyxl.reader.excel import load_workbook
from contacts_excel_dao import ContactsExcelParser
from order_excel_dao import OrderExcelParser
from json_generators import generate_invoices_json
from order_summary_export import aggregate_orders
import streamlit as st


# Set the feature flags
feature_flags = {"delivery_fees": False}

st.set_page_config(page_title="Invoice Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Invoice Generator")
INSTRUCTIONS = """
1. Download all the weekly order Excels from the weekly links
2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx
    - Where N is the week number and DD_MM_YYYY is the delivery date
3. Update the contacts spreadsheet with all contact info.
    Note:
    - Do not change the column titles
    - The names must exactly match those in the order spreadsheet.
4. Upload the order spreadsheets and the contacts spreadsheet below.
5. Press generate Order csv.
6. Press download to download the csv file.
"""
st.markdown(INSTRUCTIONS)


@st.cache_data
def convert_df_to_csv(df):
    """converts dataframe to csv and encodes it to utf-8 while caching to avoid re-computation"""
    return df.to_csv(index=False).encode('utf-8')


order_sheets = st.file_uploader(
    "Choose All Weekly Order Excels For Desired Invoice Period",
    type="xlsx",
    accept_multiple_files=True,
)
if order_sheets:
    failed_files = []
    for order_sheet in order_sheets:
        expected_format = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
        if not re.search(expected_format, order_sheet.name):
            failed_files.append(order_sheet.name)
    if failed_files:
        failed_files = ", ".join([f for f in failed_files])
        st.error(
            f"Invalid order sheet name for {failed_files}. Please rename the file(s) to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx"
        )

contacts = st.file_uploader(
    "Choose Contacts Excel", type="xlsx", accept_multiple_files=False
)

if st.button("Generate Order csv"):
    if order_sheets and contacts:
        st.markdown("---")

        contacts_parser = ContactsExcelParser()
        contacts_import = contacts_parser.parse(contacts)
        contacts_import.validation_report.raise_error()

        order_parser = OrderExcelParser(contacts_import.buyers)

        markets = []

        for sheet in order_sheets:
            market_place_import = order_parser.parse(
                sheet, use_file_name_for_date=True
            )
            market_place_import.validation_report.raise_error()
            markets.append(market_place_import.market_place)

        all_orders = aggregate_orders(markets)

        st.download_button(
        label="Download Order csv",
        data=convert_df_to_csv(all_orders),
        file_name=f'Farm_to_Fork_Raw_Orders_created_{datetime.now().strftime("%Y-%m-%d")}.csv',
        mime='text/csv',
        )

else:
    st.warning(
        "Please upload weekly order spreadsheets and contacts spreadsheet and select a date."
    )
    st.stop()
