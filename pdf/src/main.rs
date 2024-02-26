use clap::{Args, Parser, Subcommand};
use f2f::{invoices::{create_invoices, read_invoice_files, Invoice}, orders::create_orders};

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
    /// Generates invoices from json file
    InvoiceDev(InvoiceDevArgs),
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

#[derive(Args)]
pub struct InvoiceDevArgs {
    /// Week formatted as MM_YYYY
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
            read_invoice_files(path, &month);
        }
        Commands::InvoiceDev(args) => {
            let path = match args.path.clone() {
                Some(p) => p,
                None => panic!("No file provided"),
            };

            let invoices = Invoice::many_from_file(path.as_path());

            create_invoices(invoices.iter().collect())
        }
    }
}
