"""
Module to generate summaries to be downloaded by the user
"""

from dataclasses import dataclass
from domain import MarketPlace, Order, Seller
import pandas as pd


@dataclass(frozen=True)
class SellerSummary:
    """
    Class to represent the summary of the orders for one seller
    """

    seller: Seller
    total_sold: float

def aggregate_orders(market_places: list[MarketPlace]) -> pd.DataFrame:
    """
    Function that aggregates the orders
    """
    all_orders: list[Order] = []
    all_sellers: set[Seller] = set()

    for market_place in market_places:
        all_orders.extend({"delivery_date": order.delivery_date.strftime("%Y-%m-%d"),
                            "seller": order.seller.name,
                            "buyer": order.buyer.name,
                            "produce": order.produce, 
                            "additional info": order.variant, 
                            "quantity": order.quantity,
                            "unit": order.unit,
                            "price": order.price/100,  
                            "total price": order.price/100 * order.quantity,
                           } for order in market_place.orders)
        all_sellers.update(market_place.sellers)

    # Save all_orders as a CSV file
    all_orders_df = pd.DataFrame(all_orders, index=None)

    return all_orders_df

def generate_seller_summaries(market_places: list[MarketPlace]) -> pd.DataFrame:
    """
    Function that calculates the summary
    """
    all_orders: list[Order] = []
    all_sellers: set[Seller] = set()

    for market_place in market_places:
        all_orders.extend(market_place.orders)
        all_sellers.update(market_place.sellers)

    seller_summaries: list[SellerSummary] = []

    for seller in all_sellers:
        total_sold = sum(
            order.price * order.quantity
            for order in all_orders
            if order.seller == seller
        )
        total_sold_export = total_sold / 100
        seller_summary = SellerSummary(seller.name, total_sold_export)
        seller_summaries.append(seller_summary)

    # Convert seller_summaries to DataFrame
    seller_summaries_df = pd.DataFrame(seller_summaries)

    return seller_summaries_df
