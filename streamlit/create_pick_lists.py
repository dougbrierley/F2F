"Create the pick lists for the sellers"

from datetime import date
from domain import MarketPlace, PickList

def create_pick_lists(market_place: MarketPlace, monday_of_order_week: date, week_number:int) -> list[PickList]:
    """
    Create the pick lists for the sellers
    """

    all_pick_lists: list[PickList] = []

    i = 0

    for seller in market_place.sellers:
        i+=1

        orders = [order for order in market_place.orders if order.seller == seller]

        if len(orders) == 0:
            i-=1
            continue

        if orders:
            all_pick_lists.append(
                PickList(
                    monday_of_order_week=monday_of_order_week,
                    seller=seller,
                    orders=frozenset(orders),
                    reference=f"F2FP{week_number}{monday_of_order_week.strftime('%Y')[2:4]}{i}"
                )
            )

    return all_pick_lists
