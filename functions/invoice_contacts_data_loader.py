import pandas as pd
import json

def load_data(file_path):
    data = pd.read_excel(file_path)
    json_data = data.to_json(orient='records')
    return json_data


print(load_data('example_data/FarmToFork_Invoice_Contacts.xlsx'))