import pandas as pd
import json
import boto3

def load_data(file_path):
    data = pd.read_excel(file_path)
    json_data = data.to_json(orient='records')
    return json_data

def handler(event, context):
    print(event, "this is the event")
    print(context, "this is the context")
    print("This has been handled")
    main()

def main():
    s3 = boto3.client('s3')
    data = s3.get_object(Bucket='serverless-s3-dev-ftfbucket-xcri21szhuya', Key='FarmToFork_Invoice_Contacts.xlsx')
    df = pd.read_excel(data["body"])
    
    


print(load_data('example_data/FarmToFork_Invoice_Contacts.xlsx'))

main()