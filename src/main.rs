use calamine::{
    open_workbook, Data, DataType, Error, Range, RangeDeserializerBuilder, Reader, Xlsx,
};
use chrono::prelude::*;
use clap::Parser;
use printpdf::*;
use std::fs::File;
use std::io::BufWriter;

struct GrowerItem {
    grower: String,
    produce_name: String,
    variant: String,
    unit: String,
    price: u32, // in pence
}

struct Buyer {
    name: String,
    index: usize,
}

impl std::fmt::Display for Buyer {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "Name: {}, Index: {}", self.name, self.index)
    }
}

struct GrowerItemOrders<'a> {
    item: GrowerItem,
    orders: Vec<(&'a Buyer, f32)>,
}

impl std::fmt::Display for GrowerItemOrders<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "Grower: {}, Produce: {}, Variant: {}, Unit: {}, Price: {}",
            self.item.grower,
            self.item.produce_name,
            self.item.variant,
            self.item.unit,
            self.item.price
        )?;
        for (buyer, order) in &self.orders {
            write!(f, "\n\t{}: {}", buyer, order)?;
        }
        Ok(())
    }
}

struct Order {
    buyer: String,
    lines: Vec<OrderLine>,
}

struct OrderLine {
    grower: String,
    produce: String,
    variant: String,
    unit: String,
    price: u32,
    qty: f32,
}

/**
 * Get the headers which are in the 3rd row
 */
fn headers(range: &mut Range<Data>) -> Vec<String> {
    range
        .rows()
        .nth(2)
        .unwrap()
        .iter()
        .map(|c| c.to_string())
        .collect()
}

fn summarise_grower_item_orders(grower_item_orders: &Vec<GrowerItemOrders>) {
    let mut grower_and_totals = std::collections::HashMap::<String, u32>::new();

    for grower_item_order in grower_item_orders {
        let total_orders: f32 = grower_item_order
            .orders
            .iter()
            .map(|(_, order)| *order as f32)
            .sum();
        let grower_total = grower_and_totals
            .entry(grower_item_order.item.grower.clone())
            .or_insert(0);
        *grower_total += (total_orders * grower_item_order.item.price as f32) as u32;
    }
    println!("{:?}", grower_and_totals);
}

fn get_buyers(headers: &Vec<String>) -> (Vec<Buyer>, usize) {
    let buyer_start = headers.iter().position(|h| h == "BUYERS:").unwrap();
    (
        headers
            .iter()
            .skip(buyer_start + 1)
            .filter(|h| h.as_str() != "")
            .enumerate()
            .map(|(i, h)| Buyer {
                name: h.to_string(),
                index: i + buyer_start,
            })
            .collect(),
        buyer_start,
    )
}

fn format_currency(pence: u32) -> String {
    let pounds = pence / 100;
    let pence = pence % 100;
    format!("£{}.{}", pounds, pence)
}

fn add_order_line(
    current_layer: &PdfLayerReference,
    order_line: &OrderLine,
    font: &IndirectFontRef,
    y_tracker_mm: f32,
) {
    current_layer.set_font(&font, 12.0);

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.write_text(&order_line.grower, &font);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(50.0), Mm(y_tracker_mm));
    current_layer.write_text(&order_line.produce, &font);
    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(90.0), Mm(y_tracker_mm));
    current_layer.write_text(&order_line.variant, &font);

    current_layer.set_text_cursor(Mm(130.0), Mm(y_tracker_mm));
    current_layer.write_text(&order_line.qty.to_string(), &font);
    current_layer.end_text_section();

    let outline_color_2 = Color::Greyscale(Greyscale::new(0.45, None));
    current_layer.set_outline_color(outline_color_2);
    current_layer.set_outline_thickness(0.5);

    let line2 = Line::from_iter(vec![
        (Point::new(Mm(10.0), Mm(y_tracker_mm - 1.2)), false),
        (Point::new(Mm(200.0), Mm(y_tracker_mm - 1.2)), false),
    ]);

    // draw second line
    current_layer.add_line(line2);
}

fn add_order_lines_to_pdf(current_layer: &PdfLayerReference, font: &IndirectFontRef, order_lines: &Vec<OrderLine>) {

    let mut y_tracker_mm = 200.0;
    for order_line in order_lines {
        add_order_line(current_layer, order_line, font, y_tracker_mm);
        y_tracker_mm -= 6.0;
    }
}

    
fn create_buyer_orders(orders: Vec<&Order>) {
    for order in orders {
        create_buyer_order(order)
    }
}


fn create_buyer_order(order: &Order) {
    let (doc, page1, layer1) =
        PdfDocument::new("PDF_Document_title", Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

    let mut y_tracker_mm = 267.0;

    let medium = doc
        .add_external_font(File::open("assets/fonts/Roboto-Medium.ttf").unwrap())
        .unwrap();
    let normal_roboto = doc
        .add_external_font(File::open("assets/fonts/Roboto-Regular.ttf").unwrap())
        .unwrap();

    current_layer.begin_text_section();

    current_layer.set_font(&normal_roboto, 46.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_line_height(8.0);
    current_layer.set_word_spacing(0.0);
    current_layer.set_character_spacing(0.0);

    current_layer.write_text("ORDER", &medium);

    current_layer.end_text_section();

    current_layer.begin_text_section();
    y_tracker_mm -= 18.0;
    current_layer.set_font(&normal_roboto, 12.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_fill_color(Color::Rgb(Rgb::new(0.0, 0.04, 0.0, None)));

    current_layer.set_line_height(14.0);
    current_layer.write_text("Order Number", &normal_roboto);
    current_layer.add_line_break();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text("00001", &normal_roboto);

    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(70.0), Mm(y_tracker_mm));

    let dt = Utc.with_ymd_and_hms(2024, 2, 20, 0, 0, 0).unwrap();

    current_layer.set_font(&normal_roboto, 12.0);
    current_layer.write_text("Date of Order", &normal_roboto);
    current_layer.add_line_break();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text(&dt.format("%d/%m/%Y").to_string(), &normal_roboto);

    current_layer.end_text_section();

    struct BuyerDetails {
        name: String,
        address1: String,
        address2: Option<String>,
        city: String,
        postcode: String,
        country: String,
    }

    let buyer_details = BuyerDetails {
        name: "Exeter College".to_string(),
        address1: "Turl Street".to_string(),
        address2: None,
        city: "Oxford".to_string(),
        postcode: "OX1 3DP".to_string(),
        country: "United Kingdom".to_string(),
    };

    current_layer.begin_text_section();

    y_tracker_mm -= 16.0;
    current_layer.set_font(&normal_roboto, 14.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.write_text("BILLED TO", &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm -= 7.0;

    current_layer.begin_text_section();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));

    current_layer.set_line_height(12.0);
    // write two lines (one line break)
    current_layer.write_text(&buyer_details.name, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.address1, &normal_roboto);
    current_layer.add_line_break();

    if let Some(address2) = &buyer_details.address2 {
        current_layer.write_text(address2, &normal_roboto);
        current_layer.add_line_break();
    }

    current_layer.write_text(&buyer_details.city, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.postcode, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.country, &normal_roboto);

    current_layer.end_text_section();

    add_order_lines_to_pdf(&current_layer, &normal_roboto, &order.lines);

    doc.save(&mut BufWriter::new(
        File::create("test_working.pdf").unwrap(),
    ))
    .unwrap();
}

fn create_pdf() {
    let (doc, page1, layer1) =
        PdfDocument::new("PDF_Document_title", Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

    let mut y_tracker_mm = 267.0;

    let medium = doc
        .add_external_font(File::open("assets/fonts/Roboto-Medium.ttf").unwrap())
        .unwrap();
    let normal_roboto = doc
        .add_external_font(File::open("assets/fonts/Roboto-Regular.ttf").unwrap())
        .unwrap();

    current_layer.begin_text_section();

    current_layer.set_font(&normal_roboto, 46.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_line_height(8.0);
    current_layer.set_word_spacing(0.0);
    current_layer.set_character_spacing(0.0);

    current_layer.write_text("INVOICE", &medium);

    current_layer.end_text_section();

    current_layer.begin_text_section();
    y_tracker_mm -= 18.0;
    current_layer.set_font(&normal_roboto, 12.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.set_fill_color(Color::Rgb(Rgb::new(0.0, 0.04, 0.0, None)));

    current_layer.set_line_height(14.0);
    current_layer.write_text("Invoice Number", &normal_roboto);
    current_layer.add_line_break();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text("00001", &normal_roboto);

    current_layer.end_text_section();

    current_layer.begin_text_section();
    current_layer.set_text_cursor(Mm(70.0), Mm(y_tracker_mm));

    let dt = Utc.with_ymd_and_hms(2024, 2, 20, 0, 0, 0).unwrap();

    current_layer.set_font(&normal_roboto, 12.0);
    current_layer.write_text("Date of Issue", &normal_roboto);
    current_layer.add_line_break();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.write_text(&dt.format("%d/%m/%Y").to_string(), &normal_roboto);

    current_layer.end_text_section();

    struct BuyerDetails {
        name: String,
        address1: String,
        address2: Option<String>,
        city: String,
        postcode: String,
        country: String,
    }

    let buyer_details = BuyerDetails {
        name: "Exeter College".to_string(),
        address1: "Turl Street".to_string(),
        address2: None,
        city: "Oxford".to_string(),
        postcode: "OX1 3DP".to_string(),
        country: "United Kingdom".to_string(),
    };

    current_layer.begin_text_section();

    y_tracker_mm -= 16.0;
    current_layer.set_font(&normal_roboto, 14.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));
    current_layer.write_text("BILLED TO", &normal_roboto);

    current_layer.end_text_section();

    y_tracker_mm -= 7.0;

    current_layer.begin_text_section();
    current_layer.set_font(&normal_roboto, 10.0);
    current_layer.set_text_cursor(Mm(10.0), Mm(y_tracker_mm));

    current_layer.set_line_height(12.0);
    // write two lines (one line break)
    current_layer.write_text(&buyer_details.name, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.address1, &normal_roboto);
    current_layer.add_line_break();

    if let Some(address2) = &buyer_details.address2 {
        current_layer.write_text(address2, &normal_roboto);
        current_layer.add_line_break();
    }

    current_layer.write_text(&buyer_details.city, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.postcode, &normal_roboto);
    current_layer.add_line_break();
    current_layer.write_text(&buyer_details.country, &normal_roboto);

    current_layer.end_text_section();

    doc.save(&mut BufWriter::new(
        File::create("test_working.pdf").unwrap(),
    ))
    .unwrap();
}

fn example(path: std::path::PathBuf) -> Result<(), Error> {
    let mut workbook: Xlsx<_> = open_workbook(path)?;
    let range_result = workbook.worksheet_range("GROWERS' PAGE");

    let mut range = match range_result {
        Ok(r) => r,
        Err(e) => panic!("Error: {}", e),
    };

    let headers = headers(&mut range);
    let (buyers, buyer_start_col) = get_buyers(&headers);

    for buyer in &buyers {
        println!("Buyer: {}", buyer);
    }

    let data = RangeDeserializerBuilder::new().from_range(&range).unwrap();

    let mut grower_item_orders_list = Vec::<GrowerItemOrders>::new();

    // Buyer -> Order
    let mut buyer_orders = std::collections::HashMap::<String, Order>::new();

    for buyer in buyers.iter() {
        buyer_orders.insert(
            buyer.name.clone(),
            Order {
                buyer: buyer.name.clone(),
                lines: Vec::new(),
            },
        );
    }

    for result in data.skip(2) {
        let grows: Vec<Data> = result.unwrap();

        if grows[1].to_string() == "" {
            continue;
        }

        // println!("{:?}", grows);

        let price = grows[4].as_f64().unwrap() * 100.0;
        let grower = grows[0].to_string();
        let produce_name = grows[1].to_string();
        let variant = grows[2].to_string();
        let unit = grows[3].to_string();

        let grower_item = GrowerItem {
            grower: grower.clone(),
            produce_name: produce_name.clone(),
            variant: variant.clone(),
            unit: unit.clone(),
            price: price as u32,
        };

        let mut grower_item_orders = GrowerItemOrders {
            item: grower_item,
            orders: Vec::new(),
        };

        for (i, buyer) in buyers.iter().enumerate() {
            let order = grows[i + buyer_start_col + 1].as_f64().unwrap();
            grower_item_orders.orders.push((&buyer, order as f32));

            buyer_orders
                .get_mut(&buyer.name)
                .unwrap()
                .lines
                .push(OrderLine {
                    grower: grower.clone(),
                    produce: produce_name.clone(),
                    variant: variant.clone(),
                    unit: unit.clone(),
                    price: price as u32,
                    qty: order as f32,
                });
        }

        grower_item_orders_list.push(grower_item_orders);
    }

    summarise_grower_item_orders(&grower_item_orders_list);

    let orders = Vec::from_iter(buyer_orders.values());

    create_buyer_orders(orders);
    Ok(())
}

#[derive(Parser)]
struct Cli {
    /// File that you want to read
    file: std::path::PathBuf,
}

fn main() {
    let args = Cli::parse();

    println!("path: {:?}", args.file);

    match example(args.file) {
        Ok(_) => println!("Success"),
        Err(e) => println!("Error: {}", e),
    }
}
