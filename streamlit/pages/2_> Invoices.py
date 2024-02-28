import streamlit as st
import pandas as pd
import boto3
import json

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

order_sheets = st.file_uploader("Choose Weekly Order Excels", type="xlsx", accept_multiple_files=True)
contacts = st.file_uploader("Choose Contacts Excel", type="xlsx", accept_multiple_files=False)

if order_sheets and contacts:
    all_orders = []
    for order_sheet in order_sheets:
        orders = pd.read_excel(order_sheet, header=2)
        contacts = pd.read_excel(contacts)

        # Remove rows with no produce name (i.e. nothing listed)
        orders = orders.dropna(subset=["Produce Name"])

        # Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
        orders = orders.loc[(orders.iloc[:, 9:].sum(axis=1) != 0)]

        # Get the names of the buyers that made orders this week
        buyers = orders.columns[9:][orders.iloc[:, 9:].sum() > 0].tolist()

        if not buyers:
            print("No buyers this week")


        invoice_data = {"orders": []}

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

        my_order_lines = []

        orders = orders.rename(
            columns={
                "Produce Name": "produce",
                "Additional Info": "variant",
                "UNIT": "unit",
                "Price/   UNIT (£)": "price",
                "Growers": "seller",
            }
        )

        orders["price"] = (orders["price"] * 100).astype(int)

        for buyer in buyers:
            # Save the rows that are non-zero for the current buyer
            non_zero_rows = orders.loc[orders[buyer] != 0]

            # Create a new dataframe with the first 8 columns of non_zero_rows and an additional column for orders[buyer]
            buyer_lines = non_zero_rows.iloc[:, :5].copy()
            buyer_lines["qty"] = non_zero_rows[buyer]
            buyer_lines.loc[:, "buyer"] = buyer

            buyer_lines = buyer_lines.to_dict(orient="records")
            for line in buyer_lines:
                my_order_lines.append(line)

        buyer_lines = {}

        selective_list = ["produce", "variant", "unit", "price", "qty"]

        for line in my_order_lines:
            if line["buyer"] not in buyer_lines or not isinstance(buyer_lines[line["buyer"]], dict):
                buyer_lines[line["buyer"]] = {}
            if line["seller"] not in buyer_lines[line["buyer"]]:
                buyer_lines[line["buyer"]][line["seller"]] = []
            line_without_buyer = {k: v for k, v in line.items() if k not in ["buyer", "seller"]}
            print("Adding", line_without_buyer, "to", line["buyer"], "from", line["seller"])
            buyer_lines[line["buyer"]][line["seller"]].append(line_without_buyer)
            print(buyer_lines[line["buyer"]])

        orders = []

        for buyer, seller_lines in buyer_lines.items():
            orders.append({"buyer": buyer, "lines": seller_lines})


        final_data = {"orders": orders}

        final_data
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
        result
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