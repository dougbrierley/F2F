import streamlit as st
import pandas as pd
import boto3
import json

st.set_page_config(page_title="Delivery Notes Generator")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

st.markdown("Upload weekly order excel and contacts CSV to generate delivery notes.")

order_sheet = st.file_uploader("Choose Weekly Order Excel", type="xlsx", accept_multiple_files=False)
contacts = st.file_uploader("Choose Contacts CSV", type="xlsx", accept_multiple_files=False)
dataframes = []

if order_sheet and contacts:
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

    invoice_data = {
        "orders": []
    }

    # Rename the columns to match the notes format
    contacts = contacts.rename(columns={
        'Buyer': 'name', 
        'Address Line 1': 'address1',
        'Address Line 2': 'adress2', 
        'City': 'city',
        'Postcode': 'postcode',
        'City': 'city', 
        'Country': 'country'
        })

    contacts = contacts.fillna("")

    for buyer in buyers:
        # Save the rows that are non-zero for the current buyer
        non_zero_rows = orders.loc[orders[buyer] != 0].reset_index(drop=True)

        # Get the unique sellers for the produce that the buyer has ordered
        sellers = non_zero_rows["Growers"].unique()

        lines = dict.fromkeys(sellers, [])
        
        for index, row in non_zero_rows.iterrows():
            if row[buyer] == 0:
                continue
            lines[row["Growers"]].append({
                "produce": row["Produce Name"],
                "variant": row["Additional Info"],
                "unit": row["UNIT"],
                "price": row["Price/   UNIT (£)"],
                "qty": row[buyer]})


        buyer_info = contacts[contacts["name"] == buyer]
        buyer_info = buyer_info.to_dict(orient="records")

        order = {
            "buyer": buyer_info,
            "lines": lines
        }

        invoice_data["orders"].append(order)

    invoice_data_json = json.dumps(invoice_data)

    Lambda = boto3.client('lambda', region_name="eu-west-2")
    response = Lambda.invoke(
        FunctionName='arn:aws:lambda:eu-west-2:850434255294:function:create_orders',
        InvocationType='RequestResponse',
        LogType='Tail',
        # ClientContext='str_jsoning',
        Payload=invoice_data,
        # Qualifier='string'
    )
    print(response)

else:
    st.warning("Please upload CSV file(s).")
    st.stop()

invoice_data


# Get all of the orders including their buyer and seller where qty non zero
# instantiate empty order list: "orders": []
# Iterate orders from 1. and create order when it doenst already exist. Also add seller if not exist

st.markdown("")
st.markdown("---")
st.markdown("")
st.markdown("<p style='text-align: center'><a href='https://github.com/Kaludii'>Github</a> | <a href='https://huggingface.co/Kaludi'>HuggingFace</a></p>", unsafe_allow_html=True)