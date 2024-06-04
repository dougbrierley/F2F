use printpdf::{ImageRotation, ImageTransform, PdfDocumentReference, Px};
use printpdf::{Color, IndirectFontRef, Mm, PdfDocument, PdfLayerReference, Rgb};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::BufWriter;

use crate::pdf::{add_hr, add_hr_width};
use crate::utils::{
    check_file_exists_and_is_json, format_currency, generate_link, upload_object, vat_rate_string,
    BuyerDetails, S3Object,
};

use std::include_bytes;
use std::path::Path;

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

// const FONT_BYTES_ROBOTO_MED: &[u8] = include_bytes!("../../assets/fonts/Roboto-Medium.ttf");
const FONT_BYTES_ROBOTO_REG: &[u8] = include_bytes!("../../assets/fonts/Roboto-Regular.ttf");
const FONT_BYTES_OSWALD: &[u8] = include_bytes!("../../assets/fonts/Oswald-Medium.ttf");
const VELOCITY_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/velocity.jpeg");
const FTF_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/Ox_Farm_to_Fork_Logo.jpg");

#[derive(Debug, Deserialize, Serialize)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct Invoice {
    buyer: BuyerDetails,
    date: String,
    due_date: String,
    reference: String,
    lines: Vec<InvoiceLine>,
}

#[derive(Debug, Deserialize, Serialize)]
/// An invoice for a buyer
pub struct InvoiceLine {
    item: String,
    price: u32,
    qty: f32,
    vat_rate: f32,
    date: String,
    seller: String,
}

impl Invoice {
    pub fn many_from_file(file_path: &Path) -> Vec<Invoice> {
        if !check_file_exists_and_is_json(file_path.to_str().unwrap()) {
            panic!("File does not exist or is not a json file");
        }
        #[derive(Debug, Deserialize)]
        struct Invoices {
            invoices: Vec<Invoice>,
        }

        let file = File::open(file_path).unwrap();
        let reader = std::io::BufReader::new(file);
        let invoices: Invoices = serde_json::from_reader(reader).unwrap();

        invoices.invoices
    }
}

fn add_table_header(current_layer: &PdfLayerReference, font: &IndirectFontRef, y_tracker_mm: f32) {
    let font_size = 12.0;

    add_hr(current_layer, y_tracker_mm + 6.0, 1.0);

    current_layer.begin_text_section();
    current_layer.use_text("DATE", font_size, Mm(10.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("ITEM", font_size, Mm(25.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("QTY", font_size, Mm(120.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("PRICE", font_size, Mm(140.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("VAT", font_size, Mm(160.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("TOTAL", font_size, Mm(180.0), Mm(y_tracker_mm), &font);
    current_layer.end_text_section();
    add_hr(current_layer, y_tracker_mm, 1.0);
}

fn add_receiver(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
    due_date: &str,
) {
    current_layer.begin_text_section();
    current_layer.set_font(&font, 10.0);
    current_layer.set_line_height(12.0);

    current_layer.use_text(
        format!("Due Date: {}", due_date),
        12.0,
        Mm(10.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        "Please make payment to",
        10.0,
        Mm(10.0),
        Mm(y_tracker_mm - 4.0),
        &font,
    );

    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_font(&font, 10.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm - 16.0));

    current_layer.set_line_height(12.0);
    // write two lines (one line break)
    current_layer.write_text("Velocity Cycle Couriers Limited", &font);
    current_layer.add_line_break();
    current_layer.write_text("Co. Reg. 06502183", &font);
    current_layer.add_line_break();
    current_layer.write_text("Starling Bank", &font);
    current_layer.add_line_break();
    current_layer.write_text("Account Number: 19501950", &font);
    current_layer.add_line_break();
    current_layer.write_text("Sort Code: 608371", &font);

    current_layer.end_text_section();
}

pub fn create_invoice_pdf(invoice: &Invoice) -> PdfDocumentReference {
    let pdf_title = format!("Order for {} {}", invoice.buyer.name, invoice.date);
    let (doc, page1, layer1) = PdfDocument::new(pdf_title, Mm(210.0), Mm(297.0), "Layer 1");
    let mut current_layer = doc.get_page(page1).get_layer(layer1);
    
    let image_velocity = image::load_from_memory(VELOCITY_BYTES_IMAGE).unwrap();
    let image = printpdf::Image::from_dynamic_image(&image_velocity);

    let rotation_center_x = Px((image.image.width.0 as f32 / 4.0) as usize);
    let rotation_center_y = Px((image.image.height.0 as f32 / 4.0) as usize);

    image.add_to_layer(
        current_layer.clone(),
        ImageTransform {
            rotate: Some(ImageRotation {
                angle_ccw_degrees: 0.0,
                rotation_center_x,
                rotation_center_y,
            }),
            scale_x: Some(1.35),
            scale_y: Some(1.35),
            translate_x: Some(Mm(145.0)),
            translate_y: Some(Mm(267.0)),
            ..Default::default()
        },
    );

    let image_velocity = image::load_from_memory(FTF_BYTES_IMAGE).unwrap();
    let image = printpdf::Image::from_dynamic_image(&image_velocity);

    let rotation_center_x = Px((image.image.width.0 as f32 / 4.0) as usize);
    let rotation_center_y = Px((image.image.height.0 as f32 / 4.0) as usize);

    image.add_to_layer(
        current_layer.clone(),
        ImageTransform {
            rotate: Some(ImageRotation {
                angle_ccw_degrees: 0.0,
                rotation_center_x,
                rotation_center_y,
            }),
            scale_x: Some(1.3),
            scale_y: Some(1.3),
            translate_x: Some(Mm(100.0)),
            translate_y: Some(Mm(260.0)),
            ..Default::default()
        },
    );


    let mut y_tracker_mm = 267.0;

    // let medium = doc.add_external_font(FONT_BYTES_ROBOTO_MED).unwrap();
    let normal_roboto = doc.add_external_font(FONT_BYTES_ROBOTO_REG).unwrap();
    let oswald = doc.add_external_font(FONT_BYTES_OSWALD).unwrap();

    current_layer.begin_text_section();

    current_layer.use_text("Company Registration No: 06502183. Registered Office: Attention: Jake Swinhoe, 38 Kennington Road, Kennington, Oxford, OX1 5PB, GBR.", 8.0, Mm(10.0), Mm(10.0), &normal_roboto);

    current_layer.set_line_height(8.0);
    current_layer.set_word_spacing(0.0);
    current_layer.set_character_spacing(0.0);

    current_layer.use_text("VAT INVOICE", 46.0, Mm(10.0), Mm(267.0), &oswald);

    y_tracker_mm -= 11.0;

    current_layer.end_text_section();

    let mut details_x = Mm(100.0);
    let font_size_details = 10.0;

    current_layer.begin_text_section();
    current_layer.set_font(&oswald, 10.0);
    current_layer.set_fill_color(Color::Rgb(Rgb::new(0.0, 0.04, 0.0, None)));

    current_layer.use_text(
        "Invoice Date",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &oswald,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        format_invoice_date(&invoice.date),
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 6.0;

    current_layer.use_text(
        "Invoice #",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &oswald,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        &invoice.buyer.number,
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 6.0;

    current_layer.use_text(
        "Reference",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &oswald,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        &invoice.reference,
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 6.0;

    current_layer.use_text(
        "VAT Number",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &oswald,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "927642308",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );

    y_tracker_mm = 256.0;

    details_x = Mm(145.0);

    current_layer.use_text(
        "Velocity Cycle Couriers Limited",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "Attention: Jake Swinhoe",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "38 Kennington Road",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "Kennington",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "Oxford",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "OX1 5PB",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );
    y_tracker_mm -= 4.0;
    current_layer.use_text(
        "GBR",
        font_size_details,
        details_x,
        Mm(y_tracker_mm),
        &normal_roboto,
    );

    y_tracker_mm = 267.0 - 12.0;

    current_layer.begin_text_section();

    current_layer.set_font(&oswald, 14.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.write_text("BILL TO", &oswald);

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
        if address2 != "" {
            current_layer.write_text(address2, &normal_roboto);
            current_layer.add_line_break();
        }
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
        &doc,
        &mut current_layer,
        &normal_roboto,
        &invoice.lines,
        &mut y_tracker_mm,
        &oswald
    );
    let summary = InvoiceSummary::from_invoice(invoice);
    
    if y_tracker_mm < 50.0 {
        current_layer = add_page(&doc);
        y_tracker_mm = 277.0;
    }
    add_total(&current_layer, &normal_roboto, y_tracker_mm, summary);

    y_tracker_mm -= 30.0;

    let due_date = chrono::NaiveDate::parse_from_str(&invoice.due_date, "%Y-%m-%d").unwrap();
    if y_tracker_mm < 50.0 {
        current_layer = add_page(&doc);
        y_tracker_mm = 277.0;
    }

    add_receiver(
        &current_layer,
        &normal_roboto,
        y_tracker_mm,
        due_date.format("%d %b %Y").to_string().as_str(),
    );

    doc
}

fn format_line_date(date: &str) -> String {
    let d = chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d").unwrap();
    d.format("%d/%m").to_string()
}

fn format_invoice_date(date: &str) -> String {
    let d = chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d").unwrap();
    d.format("%d/%m/%Y").to_string()
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
        format_line_date(&invoice_line.date),
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
        &invoice_line.qty.to_string(),
        font_size,
        Mm(120.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency(invoice_line.price),
        font_size,
        Mm(140.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        vat_rate_string(invoice_line.vat_rate),
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

fn date_as_value(date: &str) -> chrono::NaiveDate {
    let d = chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d").unwrap();
    d
}

fn order_invoice_lines_by_date(lines: &mut Vec<&InvoiceLine>) {
    lines.sort_by(|a, b| date_as_value(a.date.as_str()).cmp(&date_as_value(b.date.as_str())));
}

fn group_by_seller(lines: &Vec<InvoiceLine>) -> std::collections::HashMap<&str, Vec<&InvoiceLine>> {
    let mut grouped = std::collections::HashMap::new();

    for line in lines {
        let seller = line.seller.as_str();
        let entry = grouped.entry(seller).or_insert(Vec::new());
        entry.push(line);
    }

    for (_, lines) in &mut grouped {
        order_invoice_lines_by_date(lines);
    }

    grouped
}

fn total_per_seller_in_invoice(lines: &Vec<&InvoiceLine>) -> u32 {
    let mut total = 0;

    for line in lines {
        total += (line.qty * line.price as f32) as u32;
    }

    total
}

fn add_page(doc: &PdfDocumentReference) -> PdfLayerReference {
    let (page, layer) = doc.add_page(Mm(210.0), Mm(297.0), "layer new");
    doc.get_page(page).get_layer(layer)
}

fn add_invoice_lines_to_pdf(
    doc: &PdfDocumentReference,
    current_layer: &mut PdfLayerReference,
    font: &IndirectFontRef,
    invoice_lines: &Vec<InvoiceLine>,
    y_tracker_mm: &mut f32,
    header_font: &IndirectFontRef,
) {
    *y_tracker_mm -= 7.0;

    let grouped = group_by_seller(invoice_lines);

    for (grower, lines) in grouped {
        *y_tracker_mm -= 3.0;

        if *y_tracker_mm < 30.0 {
            *current_layer = add_page(doc);
            *y_tracker_mm = 277.0;
            add_table_header(&current_layer, header_font, *y_tracker_mm);
            *y_tracker_mm -= 7.0;
        }

        current_layer.use_text(grower, 12.0, Mm(10.0), Mm(*y_tracker_mm), font);
        current_layer.use_text(
            format_currency(total_per_seller_in_invoice(&lines)),
            12.0,
            Mm(180.0),
            Mm(*y_tracker_mm),
            font,
        );

        *y_tracker_mm -= 1.0;
        add_hr(&current_layer, *y_tracker_mm, 0.5);
        *y_tracker_mm -= 6.0;
        for line in lines {
            if *y_tracker_mm < 30.0 {
                *current_layer = add_page(doc);
                *y_tracker_mm = 277.0;
                add_table_header(&current_layer, header_font, *y_tracker_mm);
                *y_tracker_mm -= 7.0;
            }
            add_invoice_line(&current_layer, line, font, *y_tracker_mm);
            *y_tracker_mm -= 6.0;
        }
    }
}

struct InvoiceSummary {
    total: u32,
    vat: u32,
    subtotal: u32,
}

impl InvoiceSummary {
    fn from_invoice(invoice: &Invoice) -> InvoiceSummary {
        let mut subtotal = 0;
        let mut vat = 0;

        for line in &invoice.lines {
            let total = (line.qty * line.price as f32) as u32;
            subtotal += total;
            vat += (total as f32 * line.vat_rate) as u32;
        }

        InvoiceSummary {
            total: subtotal + vat,
            vat,
            subtotal,
        }
    }
}

fn add_total(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
    summary: InvoiceSummary,
) {
    let font_size = 12.0;

    add_hr(current_layer, y_tracker_mm, 1.0);

    let left = Mm(140.0);
    let right = Mm(180.0);

    current_layer.begin_text_section();
    current_layer.use_text("Subtotal", font_size, left, Mm(y_tracker_mm - 8.0), &font);
    current_layer.use_text(
        format_currency(summary.subtotal),
        font_size,
        right,
        Mm(y_tracker_mm - 8.0),
        &font,
    );

    current_layer.use_text("VAT", font_size, left, Mm(y_tracker_mm - 14.0), &font);
    current_layer.use_text(
        format_currency(summary.vat),
        font_size,
        right,
        Mm(y_tracker_mm - 14.0),
        &font,
    );
    add_hr_width(current_layer, y_tracker_mm - 14.0, 1.0, 140.0, 200.0);
    current_layer.use_text("Total", font_size, left, Mm(y_tracker_mm - 20.0), &font);
    current_layer.use_text(
        format_currency(summary.total),
        font_size,
        right,
        Mm(y_tracker_mm - 20.0),
        &font,
    );
    current_layer.end_text_section();
}

pub async fn create_invoices_s3(
    invoices: Vec<&Invoice>,
) -> Result<HashMap<String, String>, Box<dyn std::error::Error>> {
    let mut s3_objects = HashMap::new();
    for order in invoices {
        match create_invoice_s3(order).await {
            Ok(s3_object) => {
                s3_objects.insert(order.buyer.name.clone(), generate_link(&s3_object));
            }
            Err(e) => {
                return Err(e);
            }
        }
    }

    Ok(s3_objects)
}

pub fn create_invoices(invoices: Vec<&Invoice>) {
    for order in invoices {
        create_invoice(order)
    }
}

pub async fn create_invoice_s3(invoice: &Invoice) -> Result<S3Object, Box<dyn std::error::Error>> {
    let doc = create_invoice_pdf(invoice);

    let bucket_name = "farm-to-fork-pdfs";
    let key = format!(
        "Invoice {} {} {}.pdf",
        invoice.buyer.number, invoice.buyer.name, invoice.date
    );

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

pub fn create_invoice(invoice: &Invoice) {
    let doc = create_invoice_pdf(invoice);

    let path_name = format!("generated/{}.pdf", invoice.buyer.name);
    doc.save(&mut BufWriter::new(File::create(path_name).unwrap()))
        .unwrap();
}
