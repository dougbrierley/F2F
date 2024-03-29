import streamlit as st
import pandas as pd
import boto3
import json
from functions import *
import datetime
from datetime import datetime, timedelta
import re
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Invoice Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Invoice Generator")
instructions = '''
1. Download all the weekly order Excels from the weekly links
2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx
3. Update the contacts spreadsheet with all contact info.
    Note:
    - Do not change the column titles
    - The names must exactly match those in the order spreadsheet.
4. Upload the order spreadsheets and the contacts spreadsheet below.
5. Invoices are automatically generated. Click to download.
'''
st.markdown(instructions)

order_sheets = st.file_uploader("Choose All Weekly Order Excels For Desired Invoice Period", type="xlsx", accept_multiple_files=True)
if order_sheets:
    failed_files = []
    for order_sheet in order_sheets:
        expected_format = r"\d+ - \d{2}_\d{2}_\d{4}\.xlsx"
        if not re.search(expected_format, order_sheet.name):
            failed_files.append(order_sheet.name)
    if failed_files:
        failed_files = ", ".join([f for f in failed_files])
        st.error(f"Invalid order sheet name for {failed_files}. Please rename the file(s) to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx")

contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)
date = st.date_input("What's the invoice date?")

# contacts = "example_data/FarmToFork_Invoice_Contacts.xlsx"
# order_sheets = ["example_data/OxFarmToFork spreadsheet week 7 - 12_02_2024.xlsx", "example_data/OxFarmToFork spreadsheet week 9 - 26_02_2024.xlsx"]

if st.button("Generate Invoices"):
    if order_sheets and contacts and date:
        st.markdown("---")
        contacts = pd.read_excel(contacts, sheet_name="Contacts")
        contacts = contacts_formatter(contacts)

        invoice_data = []
        all_orders = pd.DataFrame()
        buyers = set()

        # Iterate through the order sheets, adding the orders to the all_orders dataframe
        for order_sheet in order_sheets:
            marketplace = pd.read_excel(order_sheet, sheet_name="GROWERS' PAGE", header=2)
            order_date = date_extractor(order_sheet)
            
            # Get the names of the buyers that made orders this week, using the "Buyers:" column as a marker
            buyers_column_index = marketplace.columns.get_loc("BUYERS:")
            new_buyers = marketplace.columns[buyers_column_index + 1:][marketplace.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()
            buyers.update(new_buyers)  # Update buyers with new_buyers

            if not new_buyers:
                st.write("No buyers this week")
                continue

            orders = orderify(marketplace)

            # Make the delivery date 8 days after the order date
            orders["date"] = (order_date + timedelta(days=8)).strftime('%Y-%m-%d')
            all_orders = pd.concat([all_orders, orders], ignore_index=True)
            
        # Add the VAT rate to the orders
        all_orders["vat_rate"] = 0

        # Add the item column to the orders
        all_orders["item"] = all_orders["produce"] + " - " + all_orders["variant"]
        columns_to_drop = ["unit", "produce", "variant"]
        all_orders = all_orders.drop(columns_to_drop, axis=1)

        # Check for unmatched buyers
        unmatched_buyers = contacts_checker(contacts["key"], buyers)

        # Top of the invoice info
        previous_month = (date - relativedelta(months=1)).strftime("%b") # Get the shortened previous month of the invoice
        previous_month_number = (date - relativedelta(months=1)).strftime("%m") # Get the number of the previous month
        reference = f"F2F-{previous_month}"
        payment_terms = 14
        due_date = (date + timedelta(days=payment_terms)).strftime("%Y-%m-%d")
        year = str(date.year)[-2:]
        i = 1

        # Iterate through the buyers and create the invoice data
        for buyer in buyers:
            # Rename the 'number' value
            contacts.loc[contacts["key"] == buyer, "number"] = f"F2F{previous_month_number}{year}{i}"

            buyer_info = contacts.loc[contacts["key"] == buyer].to_dict("records")[0]
            lines = all_orders.loc[all_orders["buyer"] == buyer].drop("buyer", axis=1)
            
            unique_dates = lines["date"].unique().tolist()

            lines = lines.to_dict("records")

            # Add delivery fee
            for delivery_date in unique_dates:
                new_line = {
                    "item": "Delivery",
                    "price": 800,
                    "seller": "Velocity",
                    "date": delivery_date,
                    "vat_rate": 0.2,
                    "qty": 1
                }
                lines.append(new_line)

            invoice_data.append({
                "date": date.strftime('%Y-%m-%d'),
                "due_date": due_date,  
                "reference": reference,
                "buyer": buyer_info,
                "lines": lines
            })
            i += 1

        final_data = {"invoices": invoice_data}
        invoice_data_json = json.dumps(final_data)
        print(invoice_data_json)

        Lambda = boto3.client('lambda', region_name="eu-west-2")
        response = Lambda.invoke(
            FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:create_invoices',
            InvocationType='RequestResponse',
            LogType='Tail',
            # ClientContext='str_jsoning',
            Payload=invoice_data_json,
            # Qualifier='string'
        )
        result = json.loads(response['Payload'].read().decode('utf-8'))
        
        i = 0
        buyers = list(buyers)
        for link in result["links"]:
            encoded_link = link.replace(" ", "%20")
            st.markdown(f"[{buyers[i]} Invoice]({encoded_link})")
            i += 1

        links_data = {"links": result["links"],
            "name": f"{date.strftime('%Y-%m-%d')} Invoice"}
            
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
        st.link_button("Download All Invoices", encoded_link)

else:
    st.warning("Please upload weekly order spreadsheet and contacts spreadsheet and select a date.")
    st.stop()
