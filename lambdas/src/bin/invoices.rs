use f2f::invoices::{create_invoices_s3, Invoice};
use lambda_runtime::{service_fn, Error, LambdaEvent};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[tokio::main]
async fn main() -> Result<(), Error> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .with_ansi(false)
        .without_time()
        .init();
    let func = service_fn(func);
    lambda_runtime::run(func).await
}

#[derive(Deserialize, Serialize, Debug)]
struct Incoming {
    invoices: Vec<Invoice>,
}

async fn func(event: LambdaEvent<Incoming>) -> Result<Value, Error> {
    let i: Vec<Invoice> = event.payload.invoices;
    tracing::info!("Received, {:?}", i);
    let refs: Vec<&Invoice> = i.iter().map(|s| s).collect();

    let links = match create_invoices_s3(refs).await {
        Ok(l) => l,
        Err(e) => {
            tracing::error!("Error: {}", e);
            panic!("Error: {}", e)
        }
    };
    Ok(json!({ "message": format!("Generated {} new invoices.", links.len()), "links": links }))
}