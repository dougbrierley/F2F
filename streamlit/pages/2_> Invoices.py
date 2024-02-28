import streamlit as st
import pandas as pd
import boto3
import json
from functions import orderify, contacts_formatter
import datetime

st.set_page_config(page_title="Invoice Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Invoice Generator")

st.markdown("Upload weekly order excel and contacts CSV to generate delivery notes.")

# order_sheets = st.file_uploader("Choose Weekly Order Excels", type="xlsx", accept_multiple_files=True)
# contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)
contacts = "example_data/FarmToFork_Invoice_Contacts.xlsx"
order_sheets = ["example_data/Farm to Fork Spreadsheet Week 43 - 23_10_2023.xlsx", "example_data/Farm to Fork Spreadsheet Week 44 - 30_10_2023.xlsx"]


if order_sheets and contacts:
    contacts = pd.read_excel(contacts)
    contacts = contacts_formatter(contacts)
    all_orders = []

    for order_sheet in order_sheets:
        marketplace = pd.read_excel(order_sheet, header=2)
        order_date = order_sheet.split(" - ")[1].split(".")[0]
        
        # Get the names of the buyers that made orders this week, using the "Buyers:" column as a marker
        buyers_column_index = marketplace.columns.get_loc("BUYERS:")
        buyers = marketplace.columns[buyers_column_index + 1:][marketplace.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()

        if not buyers:
            st.write("No buyers this week")
            continue

        orders = orderify(marketplace)

        buyer_lines = {}

        for line in orders:
            if line["buyer"] not in buyer_lines or not isinstance(buyer_lines[line["buyer"]], dict):
                buyer_lines[line["buyer"]] = {}
            if line["seller"] not in buyer_lines[line["buyer"]]:
                buyer_lines[line["buyer"]][line["seller"]] = []
            line_without_buyer = {k: v for k, v in line.items() if k not in ["buyer", "seller"]}
            # print("Adding", line_without_buyer, "to", line["buyer"], "from", line["seller"])
            buyer_lines[line["buyer"]][line["seller"]].append(line_without_buyer)
            # print(buyer_lines[line["buyer"]])

        for buyer, seller_lines in buyer_lines.items():
            orders.append({"buyer": buyer, "lines": seller_lines})


        final_data = {"orders": orders}
        final_data

        # invoice_data_json = json.dumps(final_data)

        # Lambda = boto3.client('lambda', region_name="eu-west-2")
        # response = Lambda.invoke(
        #     FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:create_invoices',
        #     InvocationType='RequestResponse',
        #     LogType='Tail',
        #     # ClientContext='str_jsoning',
        #     Payload=invoice_data_json,
        #     # Qualifier='string'
        # )
        # result = json.loads(response['Payload'].read().decode('utf-8'))
        # result
else:
    st.warning("Please upload CSV file(s).")
    st.stop()


# Get all of the orders including their buyer and seller where qty non zero
# instantiate empty order list: "orders": []
# Iterate orders from 1. and create order when it doenst already exist. Also add seller if not exist

st.markdown("")
st.markdown("---")
st.markdown("")
st.markdown("<p style='text-align: center'><a href='https://github.com/Kaludii'>Github</a> | <a href='https://huggingface.co/Kaludi'>HuggingFace</a></p>", unsafe_allow_html=True)