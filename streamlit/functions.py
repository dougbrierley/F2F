import numpy as np
import pandas as pd

def orderify(orders):
    orders = orders.replace({np.nan: ""})

    orders = orders.dropna(subset=["Produce Name"])

    # Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
    orders = orders.loc[(orders.iloc[:, 9:].sum(axis=1) != 0)]

    # Get the names of the buyers that made orders this week
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    buyers = orders.columns[buyers_column_index + 1:][orders.iloc[:, buyers_column_index + 1:].sum() > 0].tolist()

    if not buyers:
        print("No buyers this week")

    my_order_lines = []

    orders = orders.rename(columns={
        "Produce Name": "produce",
        "Additional Info": "variant",
        "UNIT": "unit",
        "Price/   UNIT (£)": "price",
        "Growers": "seller"
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

    return contacts.to_dict(orient="records")

def add_delivery_fee(orders, delivery_fee, no_deliveries):
    for order in orders:
        order.lines

    return orders