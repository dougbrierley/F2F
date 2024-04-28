"Create the delivery notes for the buyers"

from datetime import date
from domain import MarketPlace, DeliveryNote

def create_delivery_notes(market_place: MarketPlace, delivery_date: date, week_number:int) -> list[DeliveryNote]:
    """
    Create the delivery notes for the buyers
    """

    all_delivery_notes: list[DeliveryNote] = []

    i = 0

    for buyer in market_place.buyers:
        i+=1

        print(buyer)

        orders = [order for order in market_place.orders if order.buyer == buyer]

        if len(orders) == 0:
            i-=1
            continue
        
        if orders:
            all_delivery_notes.append(
                DeliveryNote(
                    note_date=delivery_date,
                    buyer=buyer,
                    orders=frozenset(orders),
                    reference=f"F2FD{week_number}{delivery_date.strftime('%Y')[2:4]}{i}"
                )
            )

    return all_delivery_notes
