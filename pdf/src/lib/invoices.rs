use chrono::prelude::*;
use printpdf::PdfDocumentReference;
use printpdf::{Color, IndirectFontRef, Mm, PdfDocument, PdfLayerReference, Rgb};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;

use crate::pdf::add_hr;
use crate::utils::{format_currency, generate_link, upload_object, S3Object};

use std::include_bytes;

pub fn read_invoice_files(path: std::path::PathBuf, month: &str) {
    let mut files = Vec::<std::path::PathBuf>::new();

    let dir = match fs::read_dir(path) {
        Ok(d) => d,
        Err(e) => {
            println!("Error: {}", e);
            return;
        }
    };

    for entry in dir {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                println!("Error: {}", e);
                continue;
            }
        };
        let path = entry.path();

        if path.is_dir() {
            continue;
        }

        let extension = match path.extension() {
            Some(e) => e,
            None => continue,
        };

        if extension != "xlsx" {
            continue;
        }

        let file_name = path.file_name().unwrap().to_str().unwrap();
        if is_in_month(file_name, &month) {
            println!("Adding: {}", file_name);
            files.push(path);
        }
    }
}

fn is_in_month(file_name: &str, month: &str) -> bool {
    let re = Regex::new(r"\b(\d{2}_\d{2}_\d{4})\b").unwrap();

    for cap in re.captures_iter(file_name) {
        let date = &cap[1];
        if date.contains(month) {
            return true;
        }
    }
    false
}

const FONT_BYTES_ROBOTO_MED: &[u8] = include_bytes!("../../assets/fonts/Roboto-Medium.ttf");
const FONT_BYTES_ROBOTO_REG: &[u8] = include_bytes!("../../assets/fonts/Roboto-Regular.ttf");
const FONT_BYTES_OSWALD: &[u8] = include_bytes!("../../assets/fonts/Oswald-Medium.ttf");

#[derive(Debug, Deserialize, Serialize)]
struct BuyerDetails {
    name: String,
    address1: String,
    address2: Option<String>,
    city: String,
    postcode: String,
    country: String,
}

#[derive(Debug, Deserialize, Serialize)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct Invoice {
    buyer: BuyerDetails,
    date: String,
    due_date: String,
    number: String,
    reference: String,
    lines: Vec<InvoiceLine>,
}

#[derive(Debug, Deserialize, Serialize)]
/// An invoice for a buyer
pub struct InvoiceLine {
    item: String,
    unit: String,
    price: u32,
    qty: f32,
    vat_rate: f32,
    date: String,
}

fn add_table_header(current_layer: &PdfLayerReference, font: &IndirectFontRef, y_tracker_mm: f32) {
    let font_size = 12.0;

    add_hr(current_layer, y_tracker_mm + 6.0, 1.0);

    current_layer.begin_text_section();
    current_layer.use_text("PRODUCE", font_size, Mm(10.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("DESCRIPTION", font_size, Mm(50.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("UNIT", font_size, Mm(120.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("QTY", font_size, Mm(140.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("PRICE", font_size, Mm(160.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("TOTAL", font_size, Mm(180.0), Mm(y_tracker_mm), &font);
    current_layer.end_text_section();
    add_hr(current_layer, y_tracker_mm, 1.0);
}

pub fn create_invoice_pdf(invoice: &Invoice) -> PdfDocumentReference {
    let pdf_title = format!("Order for {}", invoice.buyer.name);
    let (doc, page1, layer1) = PdfDocument::new(pdf_title, Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

    let mut y_tracker_mm = 267.0;

    let medium = doc.add_external_font(FONT_BYTES_ROBOTO_MED).unwrap();
    let normal_roboto = doc.add_external_font(FONT_BYTES_ROBOTO_REG).unwrap();
    let oswald = doc.add_external_font(FONT_BYTES_OSWALD).unwrap();

    current_layer.begin_text_section();

    current_layer.set_font(&oswald, 46.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_line_height(8.0);
    current_layer.set_word_spacing(0.0);
    current_layer.set_character_spacing(0.0);

    current_layer.write_text("ORDER", &oswald);

    current_layer.end_text_section();

    current_layer.begin_text_section();
    y_tracker_mm -= 18.0;
    current_layer.set_font(&oswald, 12.0);
    current_layer.set_text_cursor(Mm(140.0), Mm(y_tracker_mm));
    current_layer.set_fill_color(Color::Rgb(Rgb::new(0.0, 0.04, 0.0, None)));

    current_layer.set_line_height(14.0);
    current_layer.write_text("ORDER #", &oswald);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(180.0), Mm(y_tracker_mm));
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text("F2F0601", &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm -= 6.0;

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(140.0), Mm(y_tracker_mm));

    let dt = Utc.with_ymd_and_hms(2024, 2, 20, 0, 0, 0).unwrap();

    current_layer.set_font(&oswald, 12.0);
    current_layer.write_text("ORDER DATE", &oswald);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(180.0), Mm(y_tracker_mm));
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text(&dt.format("%d/%m/%Y").to_string(), &normal_roboto);

    current_layer.end_text_section();

    current_layer.begin_text_section();

    y_tracker_mm += 6.0;
    current_layer.set_font(&oswald, 14.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.write_text("DELIVER TO", &oswald);

    current_layer.end_text_section();

    y_tracker_mm -= 7.0;

    current_layer.begin_text_section();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));

    current_layer.set_line_height(12.0);
    // write two lines (one line break)
    current_layer.write_text(&invoice.buyer.name, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&invoice.buyer.address1, &normal_roboto);
    current_layer.add_line_break();

    if let Some(address2) = &invoice.buyer.address2 {
        current_layer.write_text(address2, &normal_roboto);
        current_layer.add_line_break();
    }

    current_layer.write_text(&invoice.buyer.city, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&invoice.buyer.postcode, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&invoice.buyer.country, &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm = 203.0;
    add_table_header(&current_layer, &oswald, y_tracker_mm);
    add_invoice_lines_to_pdf(
        &current_layer,
        &normal_roboto,
        &invoice.lines,
        &mut y_tracker_mm,
    );
    // let total = total_per_order(invoice);
    // add_total(&current_layer, &medium, &oswald, y_tracker_mm, total);

    doc
}

fn add_invoice_line(
    current_layer: &PdfLayerReference,
    invoice_line: &InvoiceLine,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
) {
    current_layer.set_font(&font, 10.0);

    let font_size = 10.0;

    current_layer.begin_text_section();
    current_layer.use_text(
        &invoice_line.date,
        font_size,
        Mm(10.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &invoice_line.item,
        font_size,
        Mm(25.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &invoice_line.unit,
        font_size,
        Mm(120.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &invoice_line.qty.to_string(),
        font_size,
        Mm(140.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency(invoice_line.price),
        font_size,
        Mm(160.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency((invoice_line.qty * invoice_line.price as f32) as u32),
        font_size,
        Mm(180.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.end_text_section();
}

fn add_invoice_lines_to_pdf(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    invoice_lines: &Vec<InvoiceLine>,
    y_tracker_mm: &mut f32,
) {
    *y_tracker_mm -= 7.0;

    for line in invoice_lines {
        add_invoice_line(current_layer, line, font, *y_tracker_mm);
        *y_tracker_mm -= 6.0;
    }
}

fn add_total(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    font_special: &IndirectFontRef,
    y_tracker_mm: f32,
    total: u32,
) {
    let font_size = 14.0;

    add_hr(current_layer, y_tracker_mm, 1.0);

    current_layer.begin_text_section();
    current_layer.use_text(
        "TOTAL",
        font_size,
        Mm(10.0),
        Mm(y_tracker_mm - 8.0),
        &font_special,
    );
    current_layer.use_text(
        format_currency(total),
        font_size,
        Mm(180.0),
        Mm(y_tracker_mm - 8.0),
        &font,
    );
    current_layer.end_text_section();
}

pub async fn create_invoices_s3(
    invoices: Vec<&Invoice>,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let mut s3_objects = Vec::<String>::new();
    for order in invoices {
        match create_invoice_s3(order).await {
            Ok(s3_object) => s3_objects.push(generate_link(&s3_object)),
            Err(e) => {
                return Err(e);
            }
        }
    }

    Ok(s3_objects)
}

pub async fn create_invoice_s3(invoice: &Invoice) -> Result<S3Object, Box<dyn std::error::Error>> {
    let doc = create_invoice_pdf(invoice);

    let bucket_name = "serverless-s3-dev-ftfbucket-xcri21szhuya";
    let key = format!("{}.pdf", invoice.buyer.name);

    let config = aws_config::load_from_env().await;
    let client = aws_sdk_s3::Client::new(&config);
    let bytes = match doc.save_to_bytes() {
        Ok(b) => b,
        Err(e) => {
            panic!("Error: {}", e);
        }
    };
    match upload_object(&client, bytes, bucket_name, &key).await {
        Ok(_) => {}
        Err(e) => {
            panic!("Error: {}", e);
        }
    }
    Ok(S3Object::new(key, bucket_name.to_string()))
}
