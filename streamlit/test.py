import pandas as pd
import numpy as np
import json

orders = pd.read_excel("example_data/OxFarmToFork 07_09_2023.xlsx", header=2)
orders = orders.dropna(subset=['Produce Name'])
contacts = pd.read_excel("example_data/FarmToFork_Invoice_Contacts.xlsx")

print(orders)   # Create a dictionary to store the JSON structure
json_data = {
    "orders": []
}


# Iterate over each unique buyer in the orders dataframe
for buyer in contacts['Buyer']:
    buyer_orders = {
        "buyer": buyer,
        "lines": {}
    }
    
    # Filter the orders dataframe for the current buyer
    buyer_df = orders[orders['Buyer'] == buyer]

    
    # Iterate over each unique seller for the current buyer
    for seller in buyer_df['Seller'].unique():
        seller_orders = []
        
        # Filter the buyer dataframe for the current seller
        seller_df = buyer_df[buyer_df['Seller'] == seller]
        
        # Iterate over each row in the seller dataframe
        for _, row in seller_df.iterrows():
            order = {
                "produce": row['Produce Name'],
                "variant": row['Variant'],
                "unit": row['Unit'],
                "price": row['Price'],
                "qty": row['Qty']
            }
            
            seller_orders.append(order)
        
        buyer_orders["lines"][seller] = seller_orders
    
    json_data["orders"].append(buyer_orders)

# Convert the dictionary to JSON string
json_string = json.dumps(json_data, indent=2)

# Write the JSON string to a file
with open("orders.json", "w") as json_file:
    json_file.write(json_string)
