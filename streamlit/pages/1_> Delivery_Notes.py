import streamlit as st
import pandas as pd
import boto3
import json
import numpy as np
import urllib.parse
from functions import orderify

st.set_page_config(page_title="Delivery Notes Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

st.markdown("Upload weekly order excel and contacts CSV to generate delivery notes.\n"
            "When the delivery notes are generated, you will be able to download them by clicking the link(s) below.")


order_sheet = st.file_uploader("Choose Weekly Order Excel", type="xlsx", accept_multiple_files=False)
contacts = st.file_uploader("Choose Contacts CSV", type="xlsx", accept_multiple_files=False)
dataframes = []

if order_sheet and contacts:
    orders = pd.read_excel(order_sheet, header=2)
    contacts = pd.read_excel(contacts)

    # orders = orders.replace({np.nan: ""})
    contacts = contacts.replace({np.nan: ""})

    my_order_lines = orderify(orders)

    # Get the names of the buyers that made orders this week
    buyers = orders.columns[9:][orders.iloc[:, 9:].sum() > 0].tolist()

    contacts = contacts.rename(
        columns={
            "Buyer": "name",
            "Address Line 1": "address1",
            "Address Line 2": "adress2",
            "City": "city",
            "Postcode": "postcode",
            "City": "city",
            "Country": "country",
        }
    )

    buyer_lines = {}

    selective_list = ["produce", "variant", "unit", "price", "qty"]

    for line in my_order_lines:
        if line["buyer"] not in buyer_lines or not isinstance(buyer_lines[line["buyer"]], dict):
            buyer_lines[line["buyer"]] = {}
        if line["seller"] not in buyer_lines[line["buyer"]]:
            buyer_lines[line["buyer"]][line["seller"]] = []
        line_without_buyer = {k: v for k, v in line.items() if k not in ["buyer", "seller"]}
        # print("Adding", line_without_buyer, "to", line["buyer"], "from", line["seller"])
        buyer_lines[line["buyer"]][line["seller"]].append(line_without_buyer)
        # print(buyer_lines[line["buyer"]])

    orders = []

    for buyer, seller_lines in buyer_lines.items():
        orders.append({"buyer": buyer, "lines": seller_lines})


    final_data = {"orders": orders}

    invoice_data_json = json.dumps(final_data)

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
else:
    st.warning("Please upload CSV file(s).")
    st.stop()


st.markdown("")
st.markdown("---")
st.markdown("")
st.markdown("<p style='text-align: center'><a href='https://github.com/Kaludii'>Github</a> | <a href='https://huggingface.co/Kaludi'>HuggingFace</a></p>", unsafe_allow_html=True)