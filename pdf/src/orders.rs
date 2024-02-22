use chrono::prelude::*;
use printpdf::{Color, IndirectFontRef, Mm, PdfDocument, PdfLayerReference, Rgb};
use std::fs::File;
use std::io::BufWriter;
use crate::pdf::add_hr;
use crate::utils::format_currency;

#[derive(Debug)]
pub struct Order {
    pub buyer: String,
    pub lines: std::collections::HashMap<String, Vec<OrderLine>>,
}
#[derive(Debug)]
pub struct OrderLine {
    pub produce: String,
    pub variant: String,
    pub unit: String,
    pub price: u32,
    pub qty: f32,
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

  struct BuyerDetails {
      name: String,
      address1: String,
      address2: Option<String>,
      city: String,
      postcode: String,
      country: String,
  }

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
