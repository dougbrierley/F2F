import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

def orderify(orders):
    orders = orders.replace({np.nan: ""})

    orders = orders.dropna(subset=["Produce Name"])

    if "BUYERS:" not in orders.columns:
        st.error("Error: Missing column 'BUYERS:' in order spreadsheet")
        print("Error: Missing column 'BUYERS:' in order spreadsheet")
        st.stop()

    # Get the names of the buyers that made orders this week
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    # Replace empty string values with 0
    orders.iloc[:, buyers_column_index + 1:] = orders.iloc[:, buyers_column_index + 1:].replace({"":0})
    

    # Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
    orders = orders.loc[(orders.iloc[:, 9:].sum(axis=1) != 0)]
    buyers = orders.columns[buyers_column_index + 1:][orders.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()

    if not buyers:
        st.success("No buyers this week")
        print("No buyers this week")

    my_order_lines = []

    column_mapping = {
        "Produce Name": "produce",
        "Additional Info": "variant",
        "UNIT": "unit",
        "Price/   UNIT (£)": "price",
        "Growers": "seller",
    }

    keys = list(column_mapping.keys())
    # Check if all keys exist in the columns of orders
    if not set(keys).issubset(set(orders.columns)):
        missing_columns = list(set(keys) - set(orders.columns))
        missing_columns_str = ", ".join(missing_columns)  # Join the missing columns into a string
        print(f"Error: Missing columns in order spreadsheet: {missing_columns_str}")
        st.error(f"Error: Missing columns in order spreadsheet: {missing_columns_str}")
        st.stop()


    orders = orders.rename(columns=column_mapping)

    print("Order spreadsheet column names are correct")
    st.toast("Order spreadsheet column names are correct")

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

    column_mapping = {
        "Buyer Key as in Spreadsheet": "key",
        "Buyer Full Name": "name",
        "Address Line 1": "address1",
        "Address Line 2": "address2",
        "City": "city",
        "Postcode": "postcode",
        "Country": "country",
        "Invoice Number": "number"
    }

    keys = list(column_mapping.keys())

    # Check if all keys exist in the columns of orders
    if not set(keys).issubset(set(contacts.columns)):
        missing_columns = list(set(keys) - set(contacts.columns))
        missing_columns_str = ", ".join(missing_columns)  # Join the missing columns into a string
        print(f"Error: Missing columns in contacts spreadsheet: {missing_columns_str}")
        st.error(f"Error: Missing columns in contacts spreadsheet: {missing_columns_str}")
        st.stop()

    contacts = contacts.rename(columns=column_mapping)
    st.toast("Contacts column names are correct")
    return contacts

    

def add_delivery_fee(orders, delivery_fee, no_deliveries):
    for order in orders:
        order.lines

    return orders

def contacts_checker(contacts, buyers):
    unmatched_buyers = []
    for buyer in buyers:
        if buyer not in contacts.tolist():
            unmatched_buyers.append(buyer)
    if unmatched_buyers:
        st.error(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        print(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        st.stop()
    else:
        st.toast("All buyers found in contacts")
        print("All buyers found in contacts") 
    return unmatched_buyers

def extract_buyer_list(orders):
    if "BUYERS:" not in orders.columns:
        st.error("Error: Missing column 'BUYERS:' in order spreadsheet")
        print("Error: Missing column 'BUYERS:' in order spreadsheet")
        st.stop()
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    buyers = orders.columns[buyers_column_index + 1:][orders.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()
    print(f"Buyer list: {buyers}")
    return buyers

def date_extractor(order_sheet):
    order_sheet = str(order_sheet)
    date_str = order_sheet.split(" - ")[-1].split(".")[0]
    dateobj = datetime.strptime(date_str, "%d_%m_%Y")
    return dateobj