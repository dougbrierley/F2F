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
print(my_order_lines)


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

print("\n\n\n", buyer_lines, "\n\n\n")

orders = []

for buyer, seller_lines in buyer_lines.items():
    orders.append({"buyer": buyer, "lines": seller_lines})


final_data = {"orders": orders}

print(final_data)

# Save final_data to a JSON file
# with open("final_data.json", "w") as json_file:
#     json.dump(final_data, json_file)


# order = {
#     "buyer": buyer_info,
#     "lines": lines
# }

# invoice_data["orders"].append(order)
# print(invoice_data)
