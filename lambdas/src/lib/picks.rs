use printpdf::{Color, IndirectFontRef, LinkAnnotation, Mm, PdfDocument, PdfLayerReference, Rgb};
use printpdf::{ImageRotation, ImageTransform, PdfDocumentReference, Px};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use crate::pdf::add_hr;
use crate::utils::{
    check_file_exists_and_is_json, format_currency, generate_link, upload_object,
    S3Object,
};

use std::include_bytes;

const FONT_BYTES_ROBOTO_MED: &[u8] = include_bytes!("../../assets/fonts/Roboto-Medium.ttf");
const FONT_BYTES_ROBOTO_REG: &[u8] = include_bytes!("../../assets/fonts/Roboto-Regular.ttf");
const FONT_BYTES_OSWALD: &[u8] = include_bytes!("../../assets/fonts/Oswald-Medium.ttf");
const VELOCITY_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/velocity.jpeg");
const FTF_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/Ox_Farm_to_Fork_Logo.jpg");

#[derive(Debug, Serialize, Deserialize)]
pub struct Seller {
    name: String,
}

#[derive(Debug, Deserialize, Serialize)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct Pick {
    seller: Seller,
    date: String,
    lines: Vec<PickLine>,
    reference: String,
}

impl Pick {
    pub fn many_from_file(file_path: &Path) -> Vec<Pick> {
        if !check_file_exists_and_is_json(file_path.to_str().unwrap()) {
            panic!("File does not exist or is not a json file");
        }
        #[derive(Debug, Deserialize)]
        struct Picks {
            picks: Vec<Pick>,
        }

        let file = File::open(file_path).unwrap();
        let reader = std::io::BufReader::new(file);
        let pick: Picks = serde_json::from_reader(reader).unwrap();

        pick.picks
    }
}

#[derive(Debug, Deserialize, Serialize, Clone)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct PickLine {
    produce: String,
    variant: String,
    unit: String,
    price: u32,
    qty: f32,
    buyer: String,
}

fn total_per_order(lines: &Vec<PickLine>) -> u32 {
    lines.iter().map(|l| l.price * l.qty as u32).sum()
}

fn add_table_header(current_layer: &PdfLayerReference, font: &IndirectFontRef, y_tracker_mm: f32) {
    let font_size = 12.0;

    add_hr(current_layer, y_tracker_mm + 6.0, 1.0);

    current_layer.begin_text_section();
    current_layer.use_text("PRODUCE", font_size, Mm(10.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("DESCRIPTION", font_size, Mm(50.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("QTY", font_size, Mm(115.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("UNIT", font_size, Mm(135.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("PRICE", font_size, Mm(160.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("TOTAL", font_size, Mm(180.0), Mm(y_tracker_mm), &font);
    current_layer.end_text_section();
    add_hr(current_layer, y_tracker_mm, 1.0);
}

fn create_buyer_order(order: &Pick) {
    let doc = create_buyer_order_pdf(order);
    let path_name = format!("generated/{}.pdf", order.seller.name);
    doc.save(&mut BufWriter::new(File::create(path_name).unwrap()))
        .unwrap();
}

pub fn create_buyer_order_pdf(pick: &Pick) -> PdfDocumentReference {
    let pdf_title = format!(
        "Pick {} {}.pdf",
        pick.seller.name, pick.date
    );
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

    let medium = doc.add_external_font(FONT_BYTES_ROBOTO_MED).unwrap();
    let normal_roboto = doc.add_external_font(FONT_BYTES_ROBOTO_REG).unwrap();
    let oswald = doc.add_external_font(FONT_BYTES_OSWALD).unwrap();

    current_layer.begin_text_section();

    current_layer.set_font(&oswald, 46.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_line_height(8.0);
    current_layer.set_word_spacing(0.0);
    current_layer.set_character_spacing(0.0);

    current_layer.write_text("PICK LIST", &oswald);

    current_layer.end_text_section();

    current_layer.use_text(&pick.seller.name, 20.0, Mm(10.0), Mm(245.0), &medium);

    current_layer.begin_text_section();

    current_layer.use_text(
        "If you have any questions, please contact: oxfarmtofork@gfo.org.uk",
        8.0,
        Mm(10.0),
        Mm(10.0),
        &normal_roboto,
    );
    current_layer.add_link_annotation(LinkAnnotation::new(
        printpdf::Rect::new(Mm(62.0), Mm(8.0), Mm(93.0), Mm(14.0)),
        None,
        None,
        printpdf::Actions::uri("mailto:oxfarmtofork@gfo.org.uk".to_string()),
        None,
    ));
    y_tracker_mm -= 32.0;

    current_layer.set_fill_color(Color::Rgb(Rgb::new(0.0, 0.04, 0.0, None)));
    current_layer.use_text("PICK #", 12.0, Mm(120.0), Mm(y_tracker_mm), &oswald);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(180.0), Mm(y_tracker_mm));
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text(&pick.reference, &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm -= 6.0;

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(120.0), Mm(y_tracker_mm));

    let dt = chrono::NaiveDate::parse_from_str(&pick.date, "%Y-%m-%d").unwrap();

    current_layer.set_font(&oswald, 12.0);
    current_layer.write_text("ORDER WEEK STARTING:", &oswald);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(180.0), Mm(y_tracker_mm));
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text(&dt.format("%d/%m/%Y").to_string(), &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm = 217.0;
    add_table_header(&current_layer, &oswald, y_tracker_mm);
    add_pick_lines_to_pdf(
        &doc,
        &mut current_layer,
        &normal_roboto,
        &pick.lines,
        &mut y_tracker_mm,
    );
    let total = total_per_order(&pick.lines);
    add_total(&current_layer, &medium, &oswald, y_tracker_mm, total);

    doc
}

fn add_pick_line(
    current_layer: &PdfLayerReference,
    pick_line: &PickLine,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
) {
    current_layer.set_font(&font, 10.0);

    let font_size = 10.0;

    current_layer.begin_text_section();
    current_layer.use_text(
        &pick_line.produce,
        font_size,
        Mm(10.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &pick_line.variant,
        font_size,
        Mm(50.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &pick_line.qty.to_string(),
        font_size,
        Mm(115.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &pick_line.unit,
        font_size,
        Mm(135.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency(pick_line.price),
        font_size,
        Mm(160.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency((pick_line.qty * pick_line.price as f32) as u32),
        font_size,
        Mm(180.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.end_text_section();
    add_hr(current_layer, y_tracker_mm, 0.1);
}

fn group_by_seller(lines: &Vec<PickLine>) -> std::collections::HashMap<&str, Vec<PickLine>> {
    let mut grouped = std::collections::HashMap::new();

    for line in lines {
        let seller = line.buyer.as_str();
        let entry = grouped.entry(seller).or_insert(Vec::new());
        entry.push(line.clone());
    }

    grouped
}

fn add_page(doc: &PdfDocumentReference) -> PdfLayerReference {
    let (page, layer) = doc.add_page(Mm(210.0), Mm(297.0), "layer new");
    doc.get_page(page).get_layer(layer)
}

fn add_pick_lines_to_pdf(
    doc: &PdfDocumentReference,
    current_layer: &mut PdfLayerReference,
    font: &IndirectFontRef,
    order_lines: &Vec<PickLine>,
    y_tracker_mm: &mut f32,
) {
    *y_tracker_mm -= 7.0;

    let grouped = group_by_seller(order_lines);

    for (k, v) in grouped {
        *y_tracker_mm -= 3.0;

        if *y_tracker_mm < 30.0 {
            *current_layer = add_page(doc);
            *y_tracker_mm = 277.0;
            add_table_header(&current_layer, font, *y_tracker_mm);
            *y_tracker_mm -= 7.0;
        }

        current_layer.use_text(k, 12.0, Mm(10.0), Mm(*y_tracker_mm), &font);
        current_layer.use_text(
            format_currency(total_per_order(&v)),
            12.0,
            Mm(180.0),
            Mm(*y_tracker_mm),
            font,
        );
        *y_tracker_mm -= 1.0;
        add_hr(current_layer, *y_tracker_mm, 1.0);
        *y_tracker_mm -= 6.0;
        for order_line in v.iter() {
            if *y_tracker_mm < 30.0 {
                *current_layer = add_page(doc);
                *y_tracker_mm = 277.0;
                add_table_header(&current_layer, font, *y_tracker_mm);
                *y_tracker_mm -= 7.0;
            }

            add_pick_line(current_layer, &order_line, font, *y_tracker_mm);
            *y_tracker_mm -= 6.0;
        }
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

pub fn create_buyer_orders(orders: Vec<&Pick>) {
    for order in orders {
        create_buyer_order(order)
    }
}

pub async fn create_picks_s3(
    orders: Vec<&Pick>,
) -> Result<HashMap<String, String>, Box<dyn std::error::Error>> {
    let mut s3_objects = HashMap::new();
    for order in orders {
        match create_pick_s3(order).await {
            Ok(s3_object) => {
                s3_objects.insert(order.seller.name.clone(), generate_link(&s3_object));
            },
            Err(e) => {
                return Err(e);
            }
        }
    }

    Ok(s3_objects)
}

pub async fn create_pick_s3(pick: &Pick) -> Result<S3Object, Box<dyn std::error::Error>> {
    let doc = create_buyer_order_pdf(pick);

    let bucket_name = "farm-to-fork-pdfs";
    let key = format!(
        "{} Pick List {}.pdf",
        pick.seller.name, pick.date
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
