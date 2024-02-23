
use f2f::orders::{create_buyer_orders, Order};
use lambda_runtime::{service_fn, Error, LambdaEvent};
use serde::{Deserialize, Serialize};

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
    orders: Vec<Order>,
}

async fn func(event: LambdaEvent<Incoming>) -> Result<(), Error> {
    let i: Vec<Order> = event.payload.orders;
    tracing::info!("Received, {:?}", i);
    let refs: Vec<&Order> = i.iter().map(|s| s).collect();

    create_buyer_orders(refs);
    Ok(())
}