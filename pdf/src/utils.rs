pub fn format_currency(pence: u32) -> String {
  let pounds = pence / 100;
  let pence = pence % 100;
  format!("£{}.{:02}", pounds, pence)
}
