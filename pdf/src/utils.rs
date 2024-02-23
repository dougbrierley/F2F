use calamine::{Data, Range};

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