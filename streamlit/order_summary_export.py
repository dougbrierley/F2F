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

def generate_csv_export(market_places: list[MarketPlace]) -> pd.DataFrame:
    """
    Function that calculates the summary 
    """
    all_orders: list[Order] = []
    all_sellers: set[Seller] = set()

    for market_place in market_places:
        all_orders.extend(market_place.orders)
        all_sellers.update(market_place.sellers)

    # Save all_orders as a CSV file
    all_orders_df = pd.DataFrame(all_orders)
    all_orders_df.to_csv('all_orders.csv', index=False)
    seller_summaries: list[SellerSummary] = []

    for seller in all_sellers:
        total_sold = sum(order.price*order.quantity for order in all_orders if order.seller == seller)
        total_sold_export = total_sold/100
        seller_summary = SellerSummary(seller.name, total_sold_export)
        seller_summaries.append(seller_summary)

    # Convert seller_summaries to DataFrame
    seller_summaries_df = pd.DataFrame(seller_summaries)

    return seller_summaries_df
