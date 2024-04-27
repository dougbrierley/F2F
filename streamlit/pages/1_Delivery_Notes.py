"""
Delivery Note page
"""

import json
import re
import boto3
from openpyxl.reader.excel import load_workbook
from contacts_excel_dao import ContactsExcelParser
from order_excel_dao import OrderExcelParser
import streamlit as st
from create_delivery_notes import create_delivery_notes
from json_generators import generate_order_json


st.set_page_config(page_title="Delivery Notes Generator")

HIDE_STREAMLIT_STYLE = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(HIDE_STREAMLIT_STYLE, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

INSTRUCTIONS = """
1. Download the weekly order Excel from the weekly link
2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx
    - Where N is the week number and DD_MM_YYYY is the Monday of the order week
3. Update the contacts spreadsheet with all contact info.
    Note:
    - Do not change the column titles
    - The "Buyer Key as in Spreadsheet" entries must exactly match those in the order spreadsheet.
4. Upload the order spreadsheet and the contacts spreadsheet below.
5. Delivery notes are automatically generated. Click to download.
"""
st.markdown(INSTRUCTIONS)


order_sheet_file = st.file_uploader(
    "Choose Weekly Order Excel. MUST be in format: "
    "OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx",
    type="xlsx",
    accept_multiple_files=False,
)
if order_sheet_file:
    EXPECTED_FORMAT = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
    if not re.search(EXPECTED_FORMAT, order_sheet_file.name):
        st.error(
            "Invalid order sheet name. Please rename the file to the format: "
            "OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx"
        )
contacts = st.file_uploader(
    "Choose Contacts Excel", type="xlsx", accept_multiple_files=False
)
date = st.date_input("What's the delivery date?")

# prepare order number parts

if st.button("Generate Delivery Notes"):
    if order_sheet_file and contacts and date:
        st.markdown("---")

        contacts_parser = ContactsExcelParser()
        contacts_import = contacts_parser.parse(contacts)
        contacts_import.validation_report.raise_error()

        order_parser = OrderExcelParser(contacts_import.buyers)
        market_place_import = order_parser.parse(order_sheet_file, date)
        market_place_import.validation_report.raise_error()


        week_number_match = re.search(r"k (\d+)", order_sheet_file.name)
        if week_number_match:
            week_number = week_number_match.group(1)
        else:
            st.error("Invalid order sheet name. Please use the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx")

        order_data = create_delivery_notes(market_place_import.market_place, date, week_number)

        order_data_json = generate_order_json(order_data)


        Lambda = boto3.client("lambda", region_name="eu-west-2")
        response = Lambda.invoke(
            FunctionName="arn:aws:lambda:eu-west-2:850434255294:function:create_orders",
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=order_data_json,
        )
        result = json.loads(response["Payload"].read().decode("utf-8"))

        i = 0
        links = []

        for college, link in result["links"].items():
            encoded_link = link.replace(" ", "%20")
            links.append(link)
            st.markdown(
                f"[{college} Delivery Notes]({encoded_link})")
            i += 1


        links_data = {
            "links": links,
            "name": f"{date.strftime('%Y-%m-%d')} Delivery Notes",
        }
        links_json = json.dumps(links_data)
        zipped = Lambda.invoke(
            FunctionName="arn:aws:lambda:eu-west-2:850434255294:function:zipper",
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=links_json,
        )
        zipped = json.loads(zipped["Payload"].read().decode("utf-8"))
        encoded_link = zipped["zip"].replace(" ", "%20")
        st.link_button("Download All Notes", encoded_link)
    else:
        st.warning(
            "Please upload weekly order spreadsheet and contacts spreadsheet and select a date."
        )
