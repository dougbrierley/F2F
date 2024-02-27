use printpdf::{PdfLayerReference, Greyscale, Color, Line, Point, Mm};

pub fn add_hr(current_layer: &PdfLayerReference, y_tracker_mm: f32, thickness: f32) {
  let outline_color_2 = Color::Greyscale(Greyscale::new(0.45, None));
  current_layer.set_outline_color(outline_color_2);
  current_layer.set_outline_thickness(thickness);

  let line2 = Line::from_iter(vec![
      (Point::new(Mm(10.0), Mm(y_tracker_mm - 1.2)), false),
      (Point::new(Mm(200.0), Mm(y_tracker_mm - 1.2)), false),
  ]);

  // draw second line
  current_layer.add_line(line2);
}

pub fn add_hr_width(current_layer: &PdfLayerReference, y_tracker_mm: f32, thickness: f32, x_start: f32, x_end: f32) {
  let outline_color_2 = Color::Greyscale(Greyscale::new(0.45, None));
  current_layer.set_outline_color(outline_color_2);
  current_layer.set_outline_thickness(thickness);

  let line2 = Line::from_iter(vec![
      (Point::new(Mm(x_start), Mm(y_tracker_mm - 1.2)), false),
      (Point::new(Mm(x_end), Mm(y_tracker_mm - 1.2)), false),
  ]);

  // draw second line
  current_layer.add_line(line2);
}