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

#[derive(Debug, Deserialize, Serialize)]
struct Incoming {
    name: String,
    toppings: String,
}

async fn func(event: LambdaEvent<Incoming>) -> Result<(), Error> {
    let i: Incoming = event.payload;
    tracing::info!("Hello, {}! Your toppings are: {:?}", i.name, i.toppings);
    Ok(())
}