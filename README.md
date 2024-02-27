# F2F

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