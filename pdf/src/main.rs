use calamine::{
    open_workbook, Data, DataType, Error, Range, RangeDeserializerBuilder, Reader, Xlsx,
};
use clap::{Args, Parser, Subcommand};
use ftf::invoices::start_invoices;
use ftf::orders::create_buyer_order;
use ftf::orders::{Order, OrderLine};
use std::io::Write;
use termcolor::{ColorChoice, ColorSpec, StandardStream, WriteColor};

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

fn create_buyer_orders(orders: Vec<&Order>) {
    for order in orders {
        create_buyer_order(order)
    }
}

fn create_orders(path: std::path::PathBuf) -> Result<(), Error> {
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

#[derive(Parser)]
#[command(version, about, long_about = None)]
#[command(propagate_version = true)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Generates orders from given file
    Order(OrderArgs),
    /// Generates invoice for given month
    Invoice(InvoiceArgs),
}

#[derive(Args)]
struct OrderArgs {
    /// File that you want to generate orders from
    file: Option<std::path::PathBuf>,
}

#[derive(Args)]
pub struct InvoiceArgs {
    /// Week formatted as MM_YYYY
    month: Option<String>,
    path: Option<std::path::PathBuf>,
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Order(path) => {
            let path = match path.file.clone() {
                Some(p) => p,
                None => panic!("No file provided"),
            };
            let _ = create_orders(path);
            println!("Orders generated");
        }
        Commands::Invoice(args) => {
            let month = match args.month.clone() {
                Some(m) => {
                    println!("Generating invoice for month: {}", m.clone());
                    m
                }
                None => {
                    println!("Generating invoice for current month");
                    "02_2024".to_string()
                }
            };

            let path = match args.path.clone() {
                Some(p) => {
                    // Make sure its a directory
                    if p.is_dir() {
                        p
                    } else {
                        std::env::current_dir().unwrap()
                    }
                }
                None => std::env::current_dir().unwrap(),
            };
            start_invoices(path, &month);
        }
    }
}
