"""
Dataclasses for the domain model
"""

import streamlit as st
from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass(frozen=True)
class Seller:
    """
    Seller dataclass
    """
    name: str


@dataclass(frozen=True)
class Buyer:
    name: str
    key: str
    address_line_1: str
    city: str
    postcode: str
    country: str
    address_line_2: Optional[str] = None


@dataclass(frozen=True)
class Order:
    produce: str
    unit: str
    seller: Seller
    buyer: Buyer
    variant: Optional[str] = None
    price: int = 0
    quantity: float = 0.0
    vat_rate: float = 0.0
    order_date: Optional[date] = None


@dataclass(frozen=True)
class DeliveryNote:
    note_date: date
    buyer: Buyer
    reference: str
    orders: frozenset[Order]


@dataclass(frozen=True)
class Invoice:
    invoice_date: date
    buyer: Buyer
    due_date: date
    reference: str
    orders: frozenset[Order]


@dataclass(frozen=True)
class MarketPlace:
    sellers: frozenset[Seller]
    buyers: frozenset[Buyer]
    orders: frozenset[Order]
    week: int


@dataclass(frozen=True)
class ValidationError:
    """
    Error message for a validation error
    """
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """
    Holds and handles the validation errors
    """
    source: str
    errors: list[ValidationError]

    def _generate_error_message(self):
        """
        Creates error message with new lines
        """
        errors_origin = f"Errors detected in {self.source}"
        errors = '\n'.join(self.errors)
        error_message = errors_origin + "\n" + errors
        return error_message

    def raise_error(self):
        """
        checks for any errors, stops script and raises if there are any
        """
        if len(self.errors) == 0:
            st.toast(f"No errors detected in {self.source}!", icon='✅')
        else:
            error_message = self._generate_error_message()
            st.error(error_message, icon='🚨')
            st.stop()


@dataclass(frozen=True)
class MarketPlaceImport:
    """
    Class for the data out of the marketplace spreasheet
    """
    market_place: MarketPlace
    validation_report: ValidationReport


@dataclass(frozen=True)
class ContactsImport:
    """
    Class for the data out of the contacts spreadsheet
    """
    buyers: frozenset[Buyer]
    validation_report: ValidationReport
