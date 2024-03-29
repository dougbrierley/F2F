use std::path::Path;

use aws_sdk_s3 as s3;
use calamine::{Data, Range};
use s3::error::SdkError;
use s3::operation::put_object::PutObjectError;
use s3::operation::put_object::PutObjectOutput;
use s3::primitives::ByteStream;
use serde::{Deserialize, Serialize};
pub struct S3Object {
    pub key: String,
    pub bucket: String,
}

impl S3Object {
    pub fn new(key: String, bucket: String) -> Self {
        S3Object { key, bucket }
    }
}

#[derive(Debug, Deserialize, Serialize)]
pub struct BuyerDetails {
    pub name: String,
    pub address1: String,
    pub address2: Option<String>,
    pub city: String,
    pub postcode: String,
    pub country: String,
    pub number: String,
}

pub fn format_currency(pence: u32) -> String {
    let pounds = pence / 100;
    let pence = pence % 100;
    format!("£{}.{:02}", pounds, pence)
}

/**
 * Get the headers which are in the 3rd row
 */
pub fn headers(range: &mut Range<Data>) -> Vec<String> {
    range
        .rows()
        .nth(2)
        .unwrap()
        .iter()
        .map(|c| c.to_string())
        .collect()
}

pub fn generate_link(s3_object: &S3Object) -> String {
    format!(
        "https://{}.s3.eu-west-2.amazonaws.com/{}",
        s3_object.bucket, s3_object.key
    )
}

pub async fn upload_object(
    client: &aws_sdk_s3::Client,
    bytes: Vec<u8>,
    bucket_name: &str,
    key: &str,
) -> Result<PutObjectOutput, SdkError<PutObjectError>> {
    let body = ByteStream::from(bytes);
    client
        .put_object()
        .bucket(bucket_name)
        .key(key)
        .body(body)
        .send()
        .await
}

pub fn s3_link_to_object(link: &String, bucket: &String) -> S3Object {
    let key = link.split("/").last().unwrap();
    S3Object::new(key.to_string(), bucket.clone())
}

pub fn vat_rate_string(vat_rate: f32) -> String {
    if vat_rate == 0.0 {
        return "No VAT".to_string();
    }
    format!("{}%", vat_rate * 100.0)
}

pub fn check_file_exists_and_is_json(file_path: &str) -> bool {
    let path = Path::new(file_path);

    println!("Path: {:?}", path);

    if path.exists() && path.is_file() {
        if let Some(extension) = path.extension() {
            if extension == "json" {
                return true;
            }
        }
    }

    false
}
