"Create the pick lists for the sellers"

from datetime import date
from domain import MarketPlace, PickList, Buyer, Order


def create_pick_lists(
    market_place: MarketPlace, monday_of_order_week: date, week_number: int, include_summary: bool = False
) -> list[PickList]:
    """
    Create the pick lists for the sellers
    """

    all_pick_lists: list[PickList] = []

    i = 0

    for seller in market_place.sellers:
        i += 1

        orders = [order for order in market_place.orders if order.seller == seller]

        if len(orders) == 0:
            i -= 1
            continue

        if include_summary:
            temp_dict : dict[str, list[Order]] = {}
            no_price_items : list[Order] = []
            buyer=Buyer("Total", "", "", "", "", "", None)
            # Group the items by unique produce
            for order in orders:
                key=f"{order.produce}-{order.variant}"
                if key not in temp_dict:
                    temp_dict[key] = []
                temp_dict[key].append(order)
            # Sum the quanitity across the list of orders
            for key, value in temp_dict.items():
                quantity = 0
                for order in value:
                    quantity += order.quantity
                # Deep copy
                no_price=Order(
                    produce=order.produce,
                    unit=order.unit,
                    seller=order.seller,
                    variant=order.variant,
                    price=0,
                    buyer=buyer,
                    quantity=quantity
                )
                no_price_items.append(no_price)
        orders.extend(no_price_items)
        if orders:
            all_pick_lists.append(
                PickList(
                    monday_of_order_week=monday_of_order_week,
                    seller=seller,
                    orders=frozenset(orders),
                    reference=f"F2FP{week_number}{monday_of_order_week.strftime('%Y')[2:4]}{i}",
                )
            )

    return all_pick_lists
