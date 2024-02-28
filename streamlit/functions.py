import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

def orderify(orders):
    orders = orders.replace({np.nan: ""})

    orders = orders.dropna(subset=["Produce Name"])

    # Get the names of the buyers that made orders this week
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    # Replace empty string values with 0
    orders.iloc[:, buyers_column_index + 1:] = orders.iloc[:, buyers_column_index + 1:].replace({"":0})
    

    # Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
    orders = orders.loc[(orders.iloc[:, 9:].sum(axis=1) != 0)]

    buyers = orders.columns[buyers_column_index + 1:][orders.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()

    if not buyers:
        print("No buyers this week")

    my_order_lines = []

    orders = orders.rename(columns={
        "Produce Name": "produce",
        "Additional Info": "variant",
        "UNIT": "unit",
        "Price/   UNIT (£)": "price",
        "Growers": "seller",
    })

    orders["variant"] = orders["variant"].apply(lambda x: x[:25] + "..." if len(x) > 25 else x)
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

    my_order_lines = pd.DataFrame(my_order_lines)
    
    return my_order_lines  

def contacts_formatter(contacts):
    contacts = contacts.replace({np.nan: ""})
    contacts = contacts.rename(
        columns={
            "Buyer": "name",
            "Address Line 1": "address1",
            "Address Line 2": "address2",
            "City": "city",
            "Postcode": "postcode",
            "City": "city",
            "Country": "country",
            "Invoice Number": "number"
        }
    )
    contacts = contacts[["name", "address1", "address2", "city", "postcode", "country", "number"]]
    contacts = contacts.dropna(subset=["name"])  # Remove rows with no value in the "name" column
    return contacts

def add_delivery_fee(orders, delivery_fee, no_deliveries):
    for order in orders:
        order.lines

    return orders

def contacts_checker(contacts, buyers):
    unmatched_buyers = []
    for buyer in buyers:
        if buyer not in contacts.tolist():
            print(f"Buyer {buyer} not found in contacts")
            unmatched_buyers.append(buyer)
    if unmatched_buyers:
        st.warning(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        print(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        st.stop()
    else:
        st.success("All buyers found in contacts")
        print("All buyers found in contacts") 
    return unmatched_buyers

def extract_buyer_list(orders):
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    buyers = orders.columns[buyers_column_index + 1:][orders.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()
    return buyers

def date_extractor(order_sheet):
    order_sheet = str(order_sheet)
    date_str = order_sheet.split(" - ")[-1].split(".")[0]
    dateobj = datetime.strptime(date_str, "%d_%m_%Y")
    return dateobj