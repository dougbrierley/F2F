import streamlit as st
import pandas as pd
import boto3
import json
from functions import *
import re
from openpyxl.reader.excel import load_workbook

st.set_page_config(page_title="Delivery Notes Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

instructions = """
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
st.markdown(instructions)


order_sheet_file = st.file_uploader(
    "Choose Weekly Order Excel. MUST be in format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx",
    type="xlsx",
    accept_multiple_files=False,
)
if order_sheet_file:
    expected_format = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
    if not re.search(expected_format, order_sheet_file.name):
        st.error(
            "Invalid order sheet name. Please rename the file to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx"
        )
contacts = st.file_uploader(
    "Choose Contacts Excel", type="xlsx", accept_multiple_files=False
)
date = st.date_input("What's the delivery date?")

# prepare order number parts

if st.button("Generate Delivery Notes"):
    if order_sheet_file and contacts and date:
        st.markdown("---")
        order_sheet = load_order_file(order_sheet_file)

        contacts_workbook = load_workbook(contacts)
        contact_sheet = contacts_workbook["Contacts"]

        buyers, errors = contacts_uploader(contact_sheet)

        # Prepare the data for the reference number
        # Extract the week number from the order_sheet name
        week_number_match = re.search(r"k (\d+)", order_sheet_file.name)
        if week_number_match:
            week_number = week_number_match.group(1)
        else:
            st.error(
                "Invalid order sheet name. Please use the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx"
            )
        year = str(date.year)[-2:]

        orders, errors = orderify(order_sheet, buyers, errors)

        if (errors.areErrors()):
            st.error("Errors found in the order sheet. Please fix and try again.")
            for error in errors.errors:
                st.error(error)

        all_orders: list[DeliveryNote]= []
        i = 1
        buyers_with_order: list[str] = []

        # Iterate through the buyers and create the invoice data
        for buyer in buyers:
            order = DeliveryNote(date, buyer)

            order.lines = [line for line in orders if line.buyer == buyer.key]
            order.buyer.number = f"F2FD{week_number}{year}{i}"

            if (len(order.lines) > 0):
                all_orders.append(order)
                buyers_with_order.append(buyer.name)

            i += 1


        final_json_data = {"orders": [order.toJSON() for order in all_orders]}
        invoice_data_json = json.dumps(final_json_data)

        print(invoice_data_json)

        Lambda = boto3.client("lambda", region_name="eu-west-2")
        response = Lambda.invoke(
            FunctionName="arn:aws:lambda:eu-west-2:850434255294:function:create_orders",
            InvocationType="RequestResponse",
            LogType="Tail",
            # ClientContext='str_jsoning',
            Payload=invoice_data_json,
            # Qualifier='string'
        )
        result = json.loads(response["Payload"].read().decode("utf-8"))

        i = 0
        for link in result["links"]:
            encoded_link = link.replace(" ", "%20")
            st.markdown(f"[{buyers_with_order[i]} Delivery Notes]({encoded_link})")
            i += 1

        links_data = {
            "links": result["links"],
            "name": f"{date.strftime('%Y-%m-%d')} Delivery Notes",
        }
        links_json = json.dumps(links_data)
        zip = Lambda.invoke(
            FunctionName="arn:aws:lambda:eu-west-2:850434255294:function:zipper",
            InvocationType="RequestResponse",
            LogType="Tail",
            # ClientContext='str_jsoning',
            Payload=links_json,
            # Qualifier='string'
        )
        zip = json.loads(zip["Payload"].read().decode("utf-8"))
        encoded_link = zip["zip"].replace(" ", "%20")
        st.link_button("Download All Notes", encoded_link)
    else:
        st.warning(
            "Please upload weekly order spreadsheet and contacts spreadsheet and select a date."
        )
