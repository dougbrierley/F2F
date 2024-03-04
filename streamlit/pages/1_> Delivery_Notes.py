import streamlit as st
import pandas as pd
import boto3
import json
import numpy as np
import urllib.parse
from functions import orderify, contacts_checker,contacts_formatter,extract_buyer_list, date_extractor
import datetime

st.set_page_config(page_title="Delivery Notes Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

st.markdown("1. Download the weekly order Excel from the weekly link \n "
            "2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx \n "
            "3. Update the contacts spreadsheet with all contact info. \n"
            " Note: \n"
            "- Do not change the column titles\n"
            "- The names must exactly match those in the order spreadsheet.\n"
            "- The invoice number column will be printed as the delivery number on the pdf.\n"
            "4. Upload the order spreadsheet and the contacts spreadsheet below. \n"
            "5. Delivery notes are automatically generated. Click to download.")


order_sheet = st.file_uploader("Choose Weekly Order Excel", type="xlsx", accept_multiple_files=False)
contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)
date = st.date_input("What's the order date?")


if order_sheet and contacts and date:
    orders = pd.read_excel(order_sheet, header=2)
    contacts = pd.read_excel(contacts)

    # Get the names of the buyers that made orders this week
    buyers = extract_buyer_list(orders)
    # Format the contacts and orders dataframes
    contacts = contacts_formatter(contacts)
    # Check for unmatched buyers
    unmatched_buyers = contacts_checker(contacts["name"], buyers)

    orders = orderify(orders)

    buyer_json_fields = ["name", "address1", "address2", "city", "postcode", "country", "number"]

    order_json_data = []
    # Iterate through the buyers and create the invoice data
    for buyer in buyers:
        # Get the all the buyer's info
        buyer_info = contacts.loc[contacts["name"] == buyer]
        # Keep only the fields we need and convert to a dictionary
        buyer_info = buyer_info[buyer_json_fields].to_dict("records")[0]
        # Get the lines for the current buyer
        lines = orders.loc[orders["buyer"] == buyer].drop("buyer", axis=1)
        lines = lines.to_dict("records")
        order_json_data.append({
        "date": date.strftime('%Y-%m-%d'),
        "reference": "F2F-Jan",
        "buyer": buyer_info,
        "lines": lines
        })

    buyer_lines = {}

    selective_list = ["produce", "variant", "unit", "price", "qty"]

    # for line in my_order_lines:
    #     if line["buyer"] not in buyer_lines or not isinstance(buyer_lines[line["buyer"]], dict):
    #         buyer_lines[line["buyer"]] = {}
    #     if line["seller"] not in buyer_lines[line["buyer"]]:
    #         buyer_lines[line["buyer"]][line["seller"]] = []
    #     line_without_buyer = {k: v for k, v in line.items() if k not in ["buyer", "seller"]}
    #     # print("Adding", line_without_buyer, "to", line["buyer"], "from", line["seller"])
    #     buyer_lines[line["buyer"]][line["seller"]].append(line_without_buyer)
    #     # print(buyer_lines[line["buyer"]])


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
    st.warning("Please upload Excel files and select a date.")
    st.stop()
