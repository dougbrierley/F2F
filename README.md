# F2F

[![wakatime](https://wakatime.com/badge/user/018cd5cf-bd29-4404-91b8-efe68080a6a0/project/018d891a-2f85-4921-87ff-12381f17caf8.svg)](https://wakatime.com/badge/user/018cd5cf-bd29-4404-91b8-efe68080a6a0/project/018d891a-2f85-4921-87ff-12381f17caf8) ![build](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiVVRIRTY0WVRWaHBIOXlsMnkvWjdiUVVsVnUxTkd3ZkYzZFFUWUFLaUhRRXpsTUM4U1lteXlrblVGdGdGSzBjdGN2ZDlxTk1RNDkvcEtNVjBFUW1aOGlFPSIsIml2UGFyYW1ldGVyU3BlYyI6InRQUVdsc1VIRzJNQVh0SHEiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

Farm to Fork order and invoice generator.

## Streamlit

The streamlit app accepts `.xlsx` files, parses the data and generate the PDFs via the lambda functions.

To run the streamlit app, run:

```sh
streamlit run Home.py
```

## Lambdas

Two lambdas are defined in this project:

- `create_invoices`: Generates PDF invoices from orders.
- `create_orders`: Generates PDF orders from orders.

Please see the README.md for details on how to run and deploy the lambdas.