use calamine::{open_workbook, Data, DataType, Error, RangeDeserializerBuilder, Reader, Xlsx};
use chrono::prelude::*;
use printpdf::{Color, IndirectFontRef, Mm, PdfDocument, PdfLayerReference, Rgb};
use termcolor::{ColorChoice, ColorSpec, StandardStream, WriteColor};
use std::fs::File;
use std::io::BufWriter;
use std::io::Write;

use crate::pdf::add_hr;
use crate::utils::{format_currency, headers};

struct BuyerDetails {
    name: String,
    address1: String,
    address2: Option<String>,
    city: String,
    postcode: String,
    country: String,
}

#[derive(Debug)]
/// An order for a buyer along with a hashmap of produce and order lines.
pub struct Order {
    buyer: String,
    lines: std::collections::HashMap<String, Vec<OrderLine>>,
} 
#[derive(Debug)]
pub struct OrderLine {
    produce: String,
    variant: String,
    unit: String,
    price: u32,
    qty: f32,
}

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

fn total_per_grower(lines: &Vec<OrderLine>) -> u32 {
    lines.iter().map(|l| l.price * l.qty as u32).sum()
}

fn total_per_order(order: &Order) -> u32 {
    order.lines.values().map(|l| total_per_grower(l)).sum()
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

pub fn create_buyer_order(order: &Order) {
    let pdf_title = format!("Order for {}", order.buyer);
    let (doc, page1, layer1) = PdfDocument::new(pdf_title, Mm(210.0), Mm(297.0), "Layer 1");
    let current_layer = doc.get_page(page1).get_layer(layer1);

    let mut y_tracker_mm = 267.0;

    let medium = doc
        .add_external_font(File::open("assets/fonts/Roboto-Medium.ttf").unwrap())
        .unwrap();
    let normal_roboto = doc
        .add_external_font(File::open("assets/fonts/Roboto-Regular.ttf").unwrap())
        .unwrap();
    let oswald = doc
        .add_external_font(File::open("assets/fonts/Oswald-Medium.ttf").unwrap())
        .unwrap();

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



    let buyer_details = BuyerDetails {
        name: order.buyer.clone(),
        address1: "Turl Street".to_string(),
        address2: None,
        city: "Oxford".to_string(),
        postcode: "OX1 3DP".to_string(),
        country: "United Kingdom".to_string(),
    };

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

    y_tracker_mm = 203.0;
    add_table_header(&current_layer, &oswald, y_tracker_mm);
    add_order_lines_to_pdf(
        &current_layer,
        &normal_roboto,
        &order.lines,
        &mut y_tracker_mm,
    );
    let total = total_per_order(order);
    add_total(&current_layer, &medium, &oswald, y_tracker_mm, total);

    let path_name = format!("generated/{}.pdf", order.buyer);

    doc.save(&mut BufWriter::new(File::create(path_name).unwrap()))
        .unwrap();
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
        Mm(120.0),
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

fn add_order_lines_to_pdf(
    current_layer: &PdfLayerReference,
    font: &IndirectFontRef,
    order_lines: &std::collections::HashMap<String, Vec<OrderLine>>,
    y_tracker_mm: &mut f32,
) {
    *y_tracker_mm -= 7.0;

    for (k, v) in order_lines {
        *y_tracker_mm -= 3.0;
        current_layer.use_text(k, 12.0, Mm(10.0), Mm(*y_tracker_mm), &font);
        current_layer.use_text(
            format_currency(total_per_grower(v)),
            12.0,
            Mm(180.0),
            Mm(*y_tracker_mm),
            font,
        );
        *y_tracker_mm -= 1.0;
        add_hr(current_layer, *y_tracker_mm, 0.5);
        *y_tracker_mm -= 6.0;
        for order_line in v {
            add_order_line(current_layer, order_line, font, *y_tracker_mm);
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

fn create_buyer_orders(orders: Vec<&Order>) {
    for order in orders {
        create_buyer_order(order)
    }
}

pub fn create_orders(path: std::path::PathBuf) -> Result<(), Error> {
    let mut workbook: Xlsx<_> = open_workbook(path)?;
    let range_result = workbook.worksheet_range("GROWERS' PAGE");

    let mut range = match range_result {
        Ok(r) => r,
        Err(e) => panic!("Error: {}", e),
    };

    let headers = headers(&mut range);
    let (buyers, buyer_start_col) = get_buyers(&headers);

    let mut stdout = StandardStream::stdout(ColorChoice::Always);

    stdout.set_color(ColorSpec::new().set_fg(Some(termcolor::Color::White)))?;
    writeln!(&mut stdout, "\nBuyers: ")?;
    writeln!(&mut stdout, "----------------------")?;

    for buyer in &buyers {
        stdout.set_color(ColorSpec::new().set_fg(Some(termcolor::Color::Cyan)))?;
        writeln!(&mut stdout, "{}", buyer.name)?;
    }

    println!("\n");

    WriteColor::reset(&mut stdout)?;

    let data = RangeDeserializerBuilder::new().from_range(&range).unwrap();

    let mut grower_item_orders_list = Vec::<GrowerItemOrders>::new();

    // Buyer -> Order
    let mut buyer_orders = std::collections::HashMap::<String, Order>::new();

    for buyer in buyers.iter() {
        buyer_orders.insert(
            buyer.name.clone(),
            Order {
                buyer: buyer.name.clone(),
                lines: std::collections::HashMap::<String, Vec<OrderLine>>::new(),
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

            if order <= 0.0 {
                continue;
            }

            grower_item_orders.orders.push((&buyer, order as f32));

            let order_line = OrderLine {
                produce: produce_name.clone(),
                variant: variant.clone(),
                unit: unit.clone(),
                price: price as u32,
                qty: order as f32,
            };

            match buyer_orders
                .get_mut(&buyer.name)
                .unwrap()
                .lines
                .entry(grower.clone())
            {
                std::collections::hash_map::Entry::Vacant(e) => {
                    e.insert(vec![order_line]);
                }
                std::collections::hash_map::Entry::Occupied(mut e) => {
                    e.get_mut().push(order_line);
                }
            }
        }

        grower_item_orders_list.push(grower_item_orders);
    }

    summarise_grower_item_orders(&grower_item_orders_list);

    print!("{:?}", buyer_orders);

    let orders = Vec::from_iter(buyer_orders.values())
        .into_iter()
        .filter(|o| o.lines.len() > 0)
        .collect::<Vec<&Order>>();

    create_buyer_orders(orders);
    Ok(())
}