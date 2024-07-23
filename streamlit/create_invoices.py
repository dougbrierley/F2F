"Create the invoices for the buyers"

from datetime import date, timedelta
from domain import MarketPlace, Invoice, Order
from dateutil.relativedelta import relativedelta


def create_invoices(
    market_places: list[MarketPlace], invoice_date: date
) -> list[Invoice]:
    """
    Create the invoices for the buyers
    """

    all_invoices: list[Invoice] = []

    i = 0
    due_date = invoice_date + timedelta(days=14)

    previous_month = (invoice_date - relativedelta(months=1)).strftime("%b")
    previous_month_number = (invoice_date - relativedelta(months=1)).strftime("%m")

    all_orders: list[Order] = []

    for market_place in market_places:
        all_orders.extend(market_place.orders)

    for buyer in market_places[0].buyers:
        i += 1

        print(buyer)

        orders = [order for order in all_orders if order.buyer == buyer]

        if len(orders) == 0:
            i -= 1
            continue

        if orders:
            all_invoices.append(
                Invoice(
                    buyer=buyer,
                    due_date=due_date,
                    invoice_date=invoice_date,
                    orders=frozenset(orders),
                    reference=f"F2F-{previous_month}",
                    invoice_number=f"F2F{previous_month_number}{invoice_date.strftime('%Y')[2:4]}{i}",
                )
            )

    return all_invoices
