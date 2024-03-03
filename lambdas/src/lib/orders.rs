use printpdf::{Color, IndirectFontRef, LinkAnnotation, Mm, PdfDocument, PdfLayerReference, Rgb};
use printpdf::{ImageRotation, ImageTransform, PdfDocumentReference, Px};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use crate::pdf::add_hr;
use crate::utils::{
    check_file_exists_and_is_json, format_currency, generate_link, upload_object, BuyerDetails,
    S3Object,
};

use std::include_bytes;

const FONT_BYTES_ROBOTO_MED: &[u8] = include_bytes!("../../assets/fonts/Roboto-Medium.ttf");
const FONT_BYTES_ROBOTO_REG: &[u8] = include_bytes!("../../assets/fonts/Roboto-Regular.ttf");
const FONT_BYTES_OSWALD: &[u8] = include_bytes!("../../assets/fonts/Oswald-Medium.ttf");
const VELOCITY_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/velocity.jpeg");
const FTF_BYTES_IMAGE: &[u8] = include_bytes!("../../assets/images/Ox_Farm_to_Fork_Logo.jpg");

#[derive(Debug, Deserialize, Serialize)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct Order {
    buyer: BuyerDetails,
    date: String,
    lines: Vec<OrderLine>,
}

impl Order {
    pub fn many_from_file(file_path: &Path) -> Vec<Order> {
        if !check_file_exists_and_is_json(file_path.to_str().unwrap()) {
            panic!("File does not exist or is not a json file");
        }
        #[derive(Debug, Deserialize)]
        struct Orders {
            orders: Vec<Order>,
        }

        let file = File::open(file_path).unwrap();
        let reader = std::io::BufReader::new(file);
        let orders: Orders = serde_json::from_reader(reader).unwrap();

        orders.orders
    }
}

#[derive(Debug, Deserialize, Serialize, Clone)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct OrderLine {
    produce: String,
    variant: String,
    unit: String,
    price: u32,
    qty: f32,
    seller: String,
}

fn total_per_order(lines: &Vec<OrderLine>) -> u32 {
    lines.iter().map(|l| l.price * l.qty as u32).sum()
}

fn add_table_header(current_layer: &PdfLayerReference, font: &IndirectFontRef, y_tracker_mm: f32) {
    let font_size = 12.0;

    add_hr(current_layer, y_tracker_mm + 6.0, 1.0);

    current_layer.begin_text_section();
    current_layer.use_text("PRODUCE", font_size, Mm(10.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("DESCRIPTION", font_size, Mm(50.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("UNIT", font_size, Mm(115.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("QTY", font_size, Mm(140.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("PRICE", font_size, Mm(160.0), Mm(y_tracker_mm), &font);
    current_layer.use_text("TOTAL", font_size, Mm(180.0), Mm(y_tracker_mm), &font);
    current_layer.end_text_section();
    add_hr(current_layer, y_tracker_mm, 1.0);
}

fn create_buyer_order(order: &Order) {
    let doc = create_buyer_order_pdf(order);
    let path_name = format!("generated/{}.pdf", order.buyer.name);
    doc.save(&mut BufWriter::new(File::create(path_name).unwrap()))
        .unwrap();
}

pub fn create_buyer_order_pdf(order: &Order) -> PdfDocumentReference {
    let pdf_title = format!("Order for {}", order.buyer.name);
    let (doc, page1, layer1) = PdfDocument::new(pdf_title, Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

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
            scale_x: Some(0.25),
            scale_y: Some(0.25),
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
            scale_x: Some(0.33),
            scale_y: Some(0.33),
            translate_x: Some(Mm(105.0)),
            translate_y: Some(Mm(263.0)),
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

    current_layer.write_text("ORDER", &oswald);

    current_layer.end_text_section();

    current_layer.begin_text_section();

    current_layer.use_text(
        "If you have any questions, please contact: hello@velocitycc.co.uk",
        8.0,
        Mm(10.0),
        Mm(10.0),
        &normal_roboto,
    );
    current_layer.add_link_annotation(LinkAnnotation::new(
        printpdf::Rect::new(Mm(62.0), Mm(8.0), Mm(93.0), Mm(14.0)),
        None,
        None,
        printpdf::Actions::uri("mailto:hello@velocitycc.co.uk".to_string()),
        None,
    ));
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
    current_layer.write_text(&order.buyer.number, &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm -= 6.0;

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(140.0), Mm(y_tracker_mm));

    let dt = chrono::NaiveDate::parse_from_str(&order.date, "%Y-%m-%d").unwrap();

    current_layer.set_font(&oswald, 12.0);
    current_layer.write_text("DELIVERY DATE", &oswald);
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
    current_layer.write_text(&order.buyer.name, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&order.buyer.address1, &normal_roboto);
    current_layer.add_line_break();

    if let Some(address2) = &order.buyer.address2 {
        if address2 != "" {
            current_layer.write_text(address2, &normal_roboto);
            current_layer.add_line_break();
        }
    }

    current_layer.write_text(&order.buyer.city, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&order.buyer.postcode, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&order.buyer.country, &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm = 203.0;
    add_table_header(&current_layer, &oswald, y_tracker_mm);
    add_order_lines_to_pdf(
        &current_layer,
        &normal_roboto,
        &order.lines,
        &mut y_tracker_mm,
    );
    let total = total_per_order(&order.lines);
    add_total(&current_layer, &medium, &oswald, y_tracker_mm, total);

    doc
}

fn add_order_line(
    current_layer: &PdfLayerReference,
    order_line: &OrderLine,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
) {
    current_layer.set_font(&font, 10.0);

    let font_size = 10.0;

    current_layer.begin_text_section();
    current_layer.use_text(
        &order_line.produce,
        font_size,
        Mm(10.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &order_line.variant,
        font_size,
        Mm(50.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &order_line.unit,
        font_size,
        Mm(115.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        &order_line.qty.to_string(),
        font_size,
        Mm(140.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency(order_line.price),
        font_size,
        Mm(160.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.use_text(
        format_currency((order_line.qty * order_line.price as f32) as u32),
        font_size,
        Mm(180.0),
        Mm(y_tracker_mm),
        &font,
    );
    current_layer.end_text_section();
}

fn group_by_seller(lines: &Vec<OrderLine>) -> std::collections::HashMap<&str, Vec<OrderLine>> {
    let mut grouped = std::collections::HashMap::new();

    for line in lines {
        let seller = line.seller.as_str();
        let entry = grouped.entry(seller).or_insert(Vec::new());
        entry.push(line.clone());
    }

    grouped
}

fn add_order_lines_to_pdf(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    order_lines: &Vec<OrderLine>,
    y_tracker_mm: &mut f32,
) {
    *y_tracker_mm -= 7.0;

    let grouped = group_by_seller(order_lines);

    for (k, v) in grouped {
        *y_tracker_mm -= 3.0;
        current_layer.use_text(k, 12.0, Mm(10.0), Mm(*y_tracker_mm), &font);
        current_layer.use_text(
            format_currency(total_per_order(&v)),
            12.0,
            Mm(180.0),
            Mm(*y_tracker_mm),
            font,
        );
        *y_tracker_mm -= 1.0;
        add_hr(current_layer, *y_tracker_mm, 0.5);
        *y_tracker_mm -= 6.0;
        for order_line in v.iter() {
            add_order_line(current_layer, &order_line, font, *y_tracker_mm);
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

pub fn create_buyer_orders(orders: Vec<&Order>) {
    for order in orders {
        create_buyer_order(order)
    }
}

pub async fn create_buyer_orders_s3(
    orders: Vec<&Order>,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let mut s3_objects = Vec::<String>::new();
    for order in orders {
        match create_buyer_order_s3(order).await {
            Ok(s3_object) => s3_objects.push(generate_link(&s3_object)),
            Err(e) => {
                return Err(e);
            }
        }
    }

    Ok(s3_objects)
}

pub async fn create_buyer_order_s3(order: &Order) -> Result<S3Object, Box<dyn std::error::Error>> {
    let doc = create_buyer_order_pdf(order);

    let bucket_name = "serverless-s3-dev-ftfbucket-xcri21szhuya";
    let key = format!("{}.pdf", order.buyer.name);

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
