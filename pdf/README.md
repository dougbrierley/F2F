# PDFs

Rust microservices that generate PDFs from orders.

## Development

### Prerequisites

- [Rust](https://www.rust-lang.org/tools/install)
- [Cargo Lambda](https://www.cargo-lambda.info/)

### Lambdas

Two lambdas are defined in this project:

- `create_invoices`: Generates PDF invoices from orders.
- `create_orders`: Generates PDF orders from orders.

### Running Locally

To run the lambdas locally, start the server watch:

```sh
cargo lambda watch
```

In another terminal, invoke the lambda that you want to test:

```sh
cargo lambda invoke create_invoices --data-file example_json/invoices.json
```

### Deploying

To deploy the lambdas, run:

```sh
cargo lambda deploy
```

This will deploy the lambdas to AWS Lambda.

## Command line tool

This project also includes a command line tool that can be used to generate PDFs from orders. To use it, run:

```sh
cargo run --bin f2f -- --help
```