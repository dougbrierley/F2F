use f2f::picks::{create_picks_s3, Pick};
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
    picks: Vec<Pick>,
    totals: Option<bool>,
}

async fn func(event: LambdaEvent<Incoming>) -> Result<Value, Error> {
    let i: Vec<Pick> = event.payload.picks;
    tracing::info!("Received, {:?}", i);
    let refs: Vec<&Pick> = i.iter().map(|s| s).collect();
    let totals: bool = match event.payload.totals  {
        Some(total) => total,
        None => true,
    };

    let links = match create_picks_s3(refs, totals).await {
        Ok(l) => l,
        Err(e) => {
            tracing::error!("Error: {}", e);
            panic!("Error: {}", e)
        }
    };

    Ok(json!({ "message": format!("Generated {} new picks.", links.len()), "links": links }))
}
