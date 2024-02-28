use aws_sdk_s3::primitives::ByteStream;
use f2f::utils::{generate_link, upload_object, S3Object};
use lambda_runtime::{service_fn, Error, LambdaEvent};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::Write;

async fn download_invoice_s3(
    key: &String,
    bucket: &String,
    s3_client: &aws_sdk_s3::Client,
) -> Result<ByteStream, Box<dyn std::error::Error>> {
    match s3_client.get_object().bucket(bucket).key(key).send().await {
        Ok(r) => return Ok(r.body),
        Err(e) => {
            panic!("Error: {}", e);
        }
    };
}

pub async fn zip_keys(
    keys: &Vec<&str>,
    bucket: &String,
) -> Result<String, Box<dyn std::error::Error>> {
    let config = aws_config::load_from_env().await;
    let client = aws_sdk_s3::Client::new(&config);

    let zip_name = "test_invoices.zip";
    let mut zip = zip::ZipWriter::new(std::fs::File::create(zip_name).unwrap());

    for key in keys {
        zip.start_file(key.to_string(), Default::default()).unwrap();
        let mut bytes = download_invoice_s3(&key.to_string(), bucket, &client)
            .await
            .unwrap();
        // let data = bytes.collect().await.unwrap().into_bytes();
        while let Some(bytes) = bytes.try_next().await.unwrap() {
            zip.write_all(&bytes).unwrap();
        }
    }

    zip.finish().unwrap();

    let bytes = std::fs::read(zip_name).unwrap();
    upload_object(&client, bytes, bucket, zip_name)
        .await
        .unwrap();
    println!("Uploaded zip");

    std::fs::remove_file(zip_name).unwrap();

    Ok(generate_link(&S3Object::new(
        zip_name.to_string(),
        bucket.clone(),
    )))
}

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
    links: Vec<String>,
}

async fn func(event: LambdaEvent<Incoming>) -> Result<Value, Error> {
    let l: Vec<String> = event.payload.links;
    tracing::info!("Received, {:?}", l);

    let keys = l
        .iter()
        .map(|link| link.split("/").last().unwrap())
        .collect::<Vec<&str>>();

    let bucket = "serverless-s3-dev-ftfbucket-xcri21szhuya".to_string();
    let zip = zip_keys(&keys, &bucket).await;

    match zip {
        Ok(z) => {
            tracing::info!("Zipped files: {}", z);
            return Ok(
                json!({ "message": format!("Generated your zip file with {} files.", l.len()), "zip": z }),
            );
        }
        Err(e) => {
            tracing::error!("Error: {}", e);
            panic!("Error: {}", e)
        }
    }
}
