use std::fs;
use regex::Regex;

pub fn start_invoices(path: std::path::PathBuf, month: &str) {
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