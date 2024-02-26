import pandas as pd
import numpy as np
import json

orders = pd.read_excel("example_data/OxFarmToFork Week 4.xlsx", header=2)
contacts = pd.read_excel("example_data/FarmToFork_Invoice_Contacts.xlsx")

# Remove rows with no produce name (i.e. nothing listed)
orders = orders.dropna(subset=["Produce Name"])

# Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
orders = orders.loc[(orders.iloc[:, 9:].sum(axis=1) != 0)]

# Get the names of the buyers that made orders this week
buyers = orders.columns[9:][orders.iloc[:, 9:].sum() > 0].tolist()

if not buyers:
    print("No buyers this week")


# invoice_data = pd.DataFrame(columns=["buyer", "seller", "produce", "variant", "unit", "price", "qty"])

invoice_data = {
    "orders": []
}



for buyer in buyers:
    # Save the rows that are non-zero for the current buyer
    non_zero_rows = orders.loc[orders[buyer] != 0].reset_index(drop=True)

    # Get the unique sellers for the produce that the buyer has ordered
    sellers = non_zero_rows["Growers"].unique()

    lines = dict.fromkeys(sellers, [])

    for index, row in non_zero_rows.iterrows():
        lines[row["Growers"]].append({
            "produce": row["Produce Name"],
            "variant": row["Additional Info"],
            "unit": row["UNIT"],
            "price": row["Price/   UNIT (£)"]*row[buyer],
            "qty": row[buyer]})
    order = {
        "buyer": buyer,
        "lines": lines
    }
    invoice_data["orders"] = order

print(invoice_data)

