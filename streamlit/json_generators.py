"JSON Generators for the Streamlit app"

import json
from domain import DeliveryNote, Invoice

def generate_order_json(orders: list[DeliveryNote]) -> list[dict]:
    """
    Generate JSON for the orders
    """

    okay = {"orders": []}

    for note in orders:
        buyer = {
            "name"      : note.buyer.name,
            "address1"  : note.buyer.address_line_1,
            "address2"  : note.buyer.address_line_2,
            "city"      : note.buyer.city,
            "postcode"  : note.buyer.postcode,
            "country"   : note.buyer.country,
            "number"    : note.reference
        }

        lines = []

        for line in note.orders:
            if line.variant is None:
                variant = ""
            else:
                variant = line.variant[:20]

            order = {
                "produce"   : line.produce,
                "variant"   : variant,
                "unit"      : line.unit,
                "price"     : line.price,
                "qty"       : line.quantity,
                "seller"    : line.seller.name,
            }

            lines.append(order)


        order = {
            "date": note.note_date.strftime("%Y-%m-%d"),
            "buyer": buyer,
            "lines": lines,
        }


        okay["orders"].append(order)

    return json.dumps(okay, indent=4)

def generate_invoices_json(invoices: list[Invoice]) -> list[dict]:
    """
    Generate JSON for the invoices
    """

    okay = {"invoices": []}

    for invoice in invoices:
        buyer = {
            "name"      : invoice.buyer.name,
            "address1"  : invoice.buyer.address_line_1,
            "address2"  : invoice.buyer.address_line_2,
            "city"      : invoice.buyer.city,
            "postcode"  : invoice.buyer.postcode,
            "country"   : invoice.buyer.country,
            "number"    : invoice.reference
        }

        lines = []

        for line in invoice.orders:
            if line.variant is None:
                variant = ""
            else:
                variant = line.variant[:20]


            order = {
                "item"      : line.produce + " - " + variant,
                "price"     : line.price,
                "qty"       : line.quantity,
                "seller"    : line.seller.name,
                "vat_rate"  : line.vat_rate,
                "date"      : line.order_date.strftime("%Y-%m-%d"),
            }

            lines.append(order)


        order = {
            "date": invoice.invoice_date.strftime("%Y-%m-%d"),
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "reference": invoice.reference,
            "buyer": buyer,
            "lines": lines,
        }

        okay["invoices"].append(order)

    return json.dumps(okay, indent=4)