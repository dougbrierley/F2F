import json
import re
import datetime
import boto3
from create_invoices import create_invoices
from datetime import datetime, timedelta
from openpyxl.reader.excel import load_workbook
from contacts_excel_dao import ContactsExcelParser
from order_excel_dao import OrderExcelParser
from json_generators import generate_invoices_json
from order_summary_export import generate_csv_export
import streamlit as st


# Set the feature flags
feature_flags = {
    "delivery_fees": False
}

st.set_page_config(page_title="Invoice Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Invoice Generator")
INSTRUCTIONS = '''
1. Download all the weekly order Excels from the weekly links
2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx
    - Where N is the week number and DD_MM_YYYY is the delivery date
3. Update the contacts spreadsheet with all contact info.
    Note:
    - Do not change the column titles
    - The names must exactly match those in the order spreadsheet.
4. Upload the order spreadsheets and the contacts spreadsheet below.
5. Invoices are automatically generated. Click to download.
'''
st.markdown(INSTRUCTIONS)

order_sheets = st.file_uploader(
    "Choose All Weekly Order Excels For Desired Invoice Period", type="xlsx", accept_multiple_files=True)
if order_sheets:
    failed_files = []
    for order_sheet in order_sheets:
        expected_format = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
        if not re.search(expected_format, order_sheet.name):
            failed_files.append(order_sheet.name)
    if failed_files:
        failed_files = ", ".join([f for f in failed_files])
        st.error(
            f"Invalid order sheet name for {failed_files}. Please rename the file(s) to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx")

contacts = st.file_uploader("Choose Contacts Excel",
                            type="xlsx", accept_multiple_files=False)
date = st.date_input("What's the invoice date?")

# contacts = "example_data/FarmToFork_Invoice_Contacts.xlsx"
# order_sheets = ["example_data/OxFarmToFork spreadsheet week 7 - 12_02_2024.xlsx", "example_data/OxFarmToFork spreadsheet week 9 - 26_02_2024.xlsx"]

if st.button("Generate Invoices"):
    if order_sheets and contacts and date:
        st.markdown("---")

        contacts_parser = ContactsExcelParser()
        contacts_import = contacts_parser.parse(contacts)
        contacts_import.validation_report.raise_error()

        order_parser = OrderExcelParser(contacts_import.buyers)

        markets = []

        for sheet in order_sheets:
            market_place_import = order_parser.parse(sheet, date, use_file_name_for_date=True)
            market_place_import.validation_report.raise_error()
            markets.append(market_place_import.market_place)

        summary = generate_seller_summaries(markets)
        st.dataframe(summary)
        invoices = create_invoices(markets, date)
        order_data_json = generate_invoices_json(invoices)

        Lambda = boto3.client('lambda', region_name="eu-west-2")
        response = Lambda.invoke(
            FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:create_invoices',
            InvocationType='RequestResponse',
            LogType='Tail',
            # ClientContext='str_jsoning',
            Payload=order_data_json,
            # Qualifier='string'
        )
        result = json.loads(response['Payload'].read().decode('utf-8'))

        i = 0

        links = []
        for college, link in result["links"].items():
            links.append(link)
            encoded_link = link.replace(" ", "%20")
            st.markdown(f"[{college} Invoice]({encoded_link})")
            i += 1

        links_data = {"links": links,
                      "name": f"{date.strftime('%Y-%m-%d')} Invoice"}

        links_json = json.dumps(links_data)
        zipper = Lambda.invoke(
            FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:zipper',
            InvocationType='RequestResponse',
            LogType='Tail',
            # ClientContext='str_jsoning',
            Payload=links_json,
            # Qualifier='string'
        )
        zipper = json.loads(zipper['Payload'].read().decode('utf-8'))
        encoded_link = zipper["zip"].replace(" ", "%20")
        st.link_button("Download All Invoices", encoded_link)

else:
    st.warning(
        "Please upload weekly order spreadsheet and contacts spreadsheet and select a date.")
    st.stop()
