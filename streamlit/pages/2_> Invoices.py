import streamlit as st
import pandas as pd
import boto3
import json
from functions import orderify, contacts_formatter, contacts_checker, date_extractor
import datetime
from datetime import datetime, timedelta

st.set_page_config(page_title="Invoice Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Invoice Generator")

st.markdown("1. Download all the weekly order Excels from the weekly links \n "
            "2. Rename the Excel to the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx \n "
            "3. Update the contacts spreadsheet with all contact info. \n"
            " Note: \n"
            "- Do not change the column titles\n"
            "- The names must exactly match those in the order spreadsheet.\n"
            "- The invoice number column will be printed as the delivery number on the pdf.\n"
            "4. Upload the order spreadsheets and the contacts spreadsheet below. \n"
            "5. Delivery notes are automatically generated. Click to download.")

order_sheets = st.file_uploader("Choose All Weekly Order Excels For Desired Invoice Period", type="xlsx", accept_multiple_files=True)
contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)
date = st.date_input("What's the Invoice date?")

# contacts = "example_data/FarmToFork_Invoice_Contacts.xlsx"
# order_sheets = ["example_data/OxFarmToFork spreadsheet week 7 - 12_02_2024.xlsx", "example_data/OxFarmToFork spreadsheet week 9 - 26_02_2024.xlsx"]

if order_sheets and contacts and date:
    contacts = pd.read_excel(contacts)
    contacts = contacts_formatter(contacts)

    # Top of the invoice info
    month = (date - timedelta(days=14)).strftime("%b") # Get the shortened month of the invoice
    reference = f"F2F-{month}"
    payment_terms = 14
    due_date = (date + timedelta(days=payment_terms)).strftime("%Y-%m-%d")
    date = date.strftime('%Y-%m-%d')

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
        # Make changes to match the invoice data structure
        orders["date"] = (order_date + timedelta(days=8)).strftime('%Y-%m-%d')
        all_orders = pd.concat([all_orders, orders], ignore_index=True)
    
    # Add the VAT rate to the orders
    all_orders["vat_rate"] = 0.2

    # Add the item column to the orders
    all_orders["item"] = all_orders["produce"] + " - " + all_orders["variant"]
    columns_to_drop = ["unit", "produce", "variant"]
    all_orders = all_orders.drop(columns_to_drop, axis=1)

    # Check for unmatched buyers
    unmatched_buyers = contacts_checker(contacts["name"], buyers)

    # Iterate through the buyers and create the invoice data
    for buyer in buyers:
        buyer_info = contacts.loc[contacts["name"] == buyer].to_dict("records")[0]
        lines = all_orders.loc[all_orders["buyer"] == buyer].drop("buyer", axis=1)
        lines = lines.to_dict("records")
        invoice_data.append({
        "date": date,
        "due_date": due_date,  # Add 14 days to the date
        "reference": reference,
        "buyer": buyer_info,
        "lines": lines
        })

    final_data = {"invoices": invoice_data}
    invoice_data_json = json.dumps(final_data)


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

else:
    st.warning("Please upload Excel file(s).")
    st.stop()

