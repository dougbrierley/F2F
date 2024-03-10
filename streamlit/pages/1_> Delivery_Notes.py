import streamlit as st
import pandas as pd
import boto3
import json
import numpy as np
from functions import *
import datetime
import re

st.set_page_config(page_title="Delivery Notes Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

instructions = '''
1. Download the weekly order Excel from the weekly link
2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx
3. Update the contacts spreadsheet with all contact info.
    Note:
    - Do not change the column titles
    - The names must exactly match those in the order spreadsheet.
4. Upload the order spreadsheet and the contacts spreadsheet below.
5. Delivery notes are automatically generated. Click to download.
'''
st.markdown(instructions)


order_sheet = st.file_uploader("Choose Weekly Order Excel. MUST be in format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx", type="xlsx", accept_multiple_files=False)
if order_sheet:
    expected_format = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
    if not re.search(expected_format, order_sheet.name):
        st.error("Invalid order sheet name. Please rename the file to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx")
contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)
date = st.date_input("What's the delivery date?")

        # prepare order number parts

if st.button("Generate Delivery Notes"):
    if order_sheet and contacts and date:
        st.markdown("---")
        orders = pd.read_excel(order_sheet, header=2)
        contacts = pd.read_excel(contacts)
        # Get the names of the buyers that made orders this week
        buyers = extract_buyer_list(orders)
        # Format the contacts and orders dataframes
        contacts = contacts_formatter(contacts)
        # Check for unmatched buyers
        unmatched_buyers = contacts_checker(contacts["key"], buyers)

        # Prepare the data for the reference number
        # Extract the week number from the order_sheet name
        week_number_match = re.search(r"week (\d+)", order_sheet.name)
        if week_number_match:
            week_number = week_number_match.group(1)
        else:
            st.error("Invalid order sheet name. Please use the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx")
        year = str(date.year)[-2:]
        
        orders = orderify(orders)

        # Write out all the columns we need from the contacts spreadsheet
        buyer_json_fields = ["name", "address1", "address2", "city", "postcode", "country", "number"]

        order_json_data = []
        i = 1
        # Iterate through the buyers and create the invoice data
        for buyer in buyers:
            # Rename the 'number' value
            contacts.loc[contacts["key"] == buyer, "number"] = f"F2F{week_number}{year}{i}"
            # Get the all the buyer's info
            buyer_info = contacts.loc[contacts["key"] == buyer]
            # Keep only the fields we need and convert to a dictionary
            buyer_info = buyer_info[buyer_json_fields].to_dict("records")[0]
            # Get the lines for the current buyer
            lines = orders.loc[orders["buyer"] == buyer].drop("buyer", axis=1)
            lines = lines.to_dict("records")
            order_json_data.append({
            "date": date.strftime('%Y-%m-%d'),
            "buyer": buyer_info,
            "lines": lines
            })
            i += 1

        final_json_data = {"orders": order_json_data}
        invoice_data_json = json.dumps(final_json_data)

        Lambda = boto3.client('lambda', region_name="eu-west-2")
        response = Lambda.invoke(
            FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:create_orders',
            InvocationType='RequestResponse',
            LogType='Tail',
            # ClientContext='str_jsoning',
            Payload=invoice_data_json,
            # Qualifier='string'
            )
        result = json.loads(response['Payload'].read().decode('utf-8'))

        i = 0
        for link in result["links"]:
            encoded_link = link.replace(" ", "%20")
            st.markdown(f"[{buyers[i]} Delivery Notes]({encoded_link})")
            i += 1
        
        links_data = {"links": result["links"],
                    "name": f"{date.strftime('%Y-%m-%d')} Delivery Notes"}
        links_json = json.dumps(links_data)
        zip = Lambda.invoke(
            FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:zipper',
            InvocationType='RequestResponse',
            LogType='Tail',
            # ClientContext='str_jsoning',
            Payload=links_json,
            # Qualifier='string'      
        )
        zip = json.loads(zip['Payload'].read().decode('utf-8'))
        encoded_link = zip["zip"].replace(" ", "%20")
        st.link_button("Download All Notes", encoded_link)
    else:
        st.warning("Please upload weekly order spreadsheet and contacts spreadsheet and select a date.")
