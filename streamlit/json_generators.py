"JSON Generators for the Streamlit app"

import json
from domain import DeliveryNote, Invoice, PickList

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
                variant = line.variant[:35]

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
            "number"    : invoice.invoice_number
        }

        lines = []

        for line in invoice.orders:
            if line.variant is None:
                variant = ""
            else:
                variant = " - " + line.variant[:35]


            order = {
                "item"      : line.produce + variant,
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

def generate_pick_list_json(pick_lists: list[PickList]) -> list[dict]:
    """
    Generate JSON for the pick lists
    """

    pick_lists_json = {"picks": []}

    for pick_list in pick_lists:
        seller = {
            "name"      : pick_list.seller.name,
        }

        lines = []

        for line in pick_list.orders:
            if line.variant is None:
                variant = ""
            else:
                variant = line.variant[:35]

            order = {
                "produce"   : line.produce,
                "variant"   : variant,
                "unit"      : line.unit,
                "price"     : line.price,
                "qty"       : line.quantity,
                "buyer"    : line.buyer.name
            }

            lines.append(order)


        pick_list_json = {
            "date": pick_list.monday_of_order_week.strftime("%Y-%m-%d"),
            "seller": seller,
            "reference"    : pick_list.reference,   
            "lines": lines,
        }


        pick_lists_json["picks"].append(pick_list_json)

    return json.dumps(pick_lists_json, indent=4)