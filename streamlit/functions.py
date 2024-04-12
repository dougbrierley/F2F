import numpy as np
import openpyxl.workbook
import openpyxl.worksheet
import openpyxl.worksheet.worksheet
import pandas as pd
import streamlit as st
from datetime import datetime
import re
from dataclasses import dataclass
import openpyxl
from typing import Optional
import json


class ExcelParsingErrors:
    warnings: list[str] = []
    errors: list[str] = []

    def warning(self, message: str):
        self.warnings.append(message)

    def error(self, message: str):
        self.errors.append(message)

    def areErrors(self):
        return len(self.errors) > 0


@dataclass()
class OrderLine:
    produce: str
    unit: str
    seller: str
    buyer: str
    variant: Optional[str] = None
    price: int = 0
    qty: float = 0.0
    vat_rat: float = 0.0
    date: Optional[datetime] = None

    def toJSONDelivery(self):
        variant = self.variant
        variant = (variant[:25] + "..") if len(variant) > 25 else variant
        return {
            "produce": self.produce,
            "variant": variant,
            "unit": self.unit,
            "price": self.price,
            "seller": self.seller,
            "qty": self.qty,
        }

    def toJSONInvoice(self):
        item = self.produce + " - " + self.variant
        item = (item[:30] + "..") if len(item) > 30 else item
        return {
            "item": item,
            "unit": self.unit,
            "price": self.price,
            "seller": self.seller,
            "qty": self.qty,
            "date": self.date.strftime("%Y-%m-%d"),
        }

    def setQuantity(
        self, qty: str, row: int, errors: ExcelParsingErrors
    ) -> ExcelParsingErrors:
        cleaned = re.sub(r"[^0-9\.]", "", qty)
        print(qty, cleaned)

        try:
            floatQty = float(cleaned)
        except ValueError:
            errors.error(f"Quantity in row {row} could not be parsed.")
            return errors

        self.qty = floatQty

        return errors

    def setPrice(
        self, price: str, row: int, errors: ExcelParsingErrors
    ) -> ExcelParsingErrors:
        cleaned = re.sub(r"[^0-9\.]", "", price)
        try:
            floatPrice = float(cleaned)
        except ValueError:
            errors.error(f"Price in row {row} could not be parsed.")
            return errors

        rounded = np.round(floatPrice * 100, decimals=0)

        try:
            integerPrice = int(rounded)
        except ValueError:
            errors.error(
                f"Price could not be parsed in row {row}, check that it has only 2 decimal places."
            )
            return errors

        self.price = integerPrice
        if integerPrice == 0:
            errors.warning(f"Price at row {row} is 0, please verify.")

        return errors

    def checkErrors(self, row: int, errors: ExcelParsingErrors) -> ExcelParsingErrors:
        for name, field_type in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                errors.error(
                    f"The {name} field on row {row} was incorrectly formatted."
                )

        return errors


@dataclass(frozen=True)
class Buyer:
    name: str
    key: str
    address1: str
    city: str
    postcode: str
    country: str
    number: Optional[str] = None
    address2: Optional[str] = None

    def toJSON(self):
        o = self.__dict__
        del o["key"]
        return o


@dataclass
class DeliveryNote:
    date: datetime
    buyer: Buyer
    lines: list[OrderLine] = []

    def addLine(self, line: OrderLine):
        self.lines.append(line)

    def toJSON(self):
        if (self.buyer.number == None):
            raise ValueError("Buyer number must be set before converting to JSON")
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "buyer": self.buyer.toJSON(),
            "lines": [x.toJSONDelivery() for x in self.lines],
        }


@dataclass
class Invoice:
    date: datetime
    buyer: Buyer
    due_date: str
    reference: str
    lines: list[OrderLine]

    def toJSON(self):
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "buyer": self.buyer.toJSON(),
            "lines": [x.toJSONInvoice() for x in self.lines],
        }


def parseOrderHeaders(
    headers: list, buyers: list[Buyer], errors: ExcelParsingErrors
) -> tuple[dict[str, int], dict[int, str], ExcelParsingErrors]:
    column_mapping = {
        "Produce Name": "produce",
        "Additional Info": "variant",
        "UNIT": "unit",
        "Price/   UNIT (£)": "price",
        "Growers": "seller",
    }

    header_dict = {
        "seller": None,
        "produce": None,
        "variant": None,
        "unit": None,
        "price": None,
    }
    buyer_keys: dict[int, str] = {}

    for key, value in column_mapping.items():
        try:
            index_of_header = headers.index(key)

        except ValueError:
            errors.error(f"Header {key} could not be found in the sheet.")

        except Exception:
            errors.error(f"Unknown error when parsing headers")

        header_dict[value] = index_of_header

    # Get buyers
    buyer_index = headers.index("BUYERS:")
    i = buyer_index + 1
    end = len(headers)

    contact_list = [buyer.key for buyer in buyers]

    for i in range(i, end):
        current_buyer = headers[i]

        if i > 100:
            errors.warning(
                f"It looks like there were lots of buyers, check that any headers without buyers are empty"
            )

        if current_buyer == None or current_buyer == "":
            continue
        
        if current_buyer not in contact_list:
            errors.error(f"Buyer {current_buyer} not found in contacts sheet.")

        buyer_keys[i] = current_buyer

    return header_dict, buyer_keys, errors


def parseQuantity(
    qty: str, row: int, buyer: str, errors: ExcelParsingErrors
) -> tuple[float, ExcelParsingErrors]:
    cleaned = re.sub(r"[^0-9\.]", "", qty)
    floatQty = 0.0
    try:
        floatQty = float(cleaned)
    except ValueError:
        errors.error(f"Quantity in row {row} for buyer {buyer} could not be parsed.")

    return floatQty, errors


def parseContactHeaders(
    headers: list, errors: ExcelParsingErrors
) -> tuple[dict[str, int], dict[int, str], ExcelParsingErrors]:
    column_mapping = {
        "Buyer Key as in Spreadsheet": "key",
        "Buyer Full Name": "name",
        "Address Line 1": "address1",
        "Address Line 2": "address2",
        "City": "city",
        "Postcode": "postcode",
        "Country": "country",
    }

    contact_header_dict = {
        "key": None,
        "name": None,
        "address1": None,
        "address2": None,
        "city": None,
        "postcode": None,
        "country": None,
    }
    buyers: dict[int, str] = {}

    for key, value in column_mapping.items():
        try:
            index_of_header = headers.index(key)

        except ValueError:
            errors.error(f"Header {key} could not be found in the contacts sheet.")

        except Exception:
            errors.error(f"Unknown error when parsing headers")

        contact_header_dict[value] = index_of_header

    return contact_header_dict, buyers, errors


def contacts_uploader(
    contacts_sheet: openpyxl.worksheet.worksheet.Worksheet,
) -> tuple[list[Buyer], ExcelParsingErrors]:
    """
    This function takes in the contacts dataframe and returns a
    list of all the buyers.
    """

    parsing_errors = ExcelParsingErrors()

    header_row = 1

    headers = contacts_sheet[header_row]
    headers = [cell.value for cell in headers]
    headers_dict, buyers, parsing_errors = parseContactHeaders(headers, parsing_errors)

    buyers: list[Buyer] = []

    i = header_row - 1

    for row in contacts_sheet.iter_rows(min_row=header_row + 1, values_only=True):
        i = i + 1

        if row[headers_dict["key"]] == None or row[headers_dict["name"]] == "":
            continue

        for buyer in buyers.items():

            buyer = Buyer(
                key=row[headers_dict["key"]],
                name=row[headers_dict["name"]],
                address1=row[headers_dict["address1"]],
                city=row[headers_dict["city"]],
                postcode=row[headers_dict["postcode"]],
                country=row[headers_dict["country"]],
                address2=row[headers_dict["address2"]],
            )

            buyers.append(buyer)

    return buyers, parsing_errors


def orderify(
    order_sheet: openpyxl.worksheet.worksheet.Worksheet,
    buyers: list[Buyer],
    parsing_errors: ExcelParsingErrors,
    order_sheet_name=None,
) -> tuple[list[OrderLine], ExcelParsingErrors]:
    """
    This function takes in the marketplace dataframe and returns a
    dataframe with each order as a separate row.
    """

    header_row = 3

    headers = order_sheet[header_row]
    headers = [cell.value for cell in headers]
    headers_dict, buyers, parsing_errors = parseOrderHeaders(headers, buyers, parsing_errors)

    order_lines: list[OrderLine] = []

    i = header_row - 1
    for row in order_sheet.iter_rows(min_row=header_row + 1, values_only=True):
        i = i + 1

        if row[headers_dict["price"]] == None or row[headers_dict["price"]] == "":
            continue

        # seller = Seller(name = row[headers_dict["seller"]])
        # sellers.add(seller)
        for index, buyer in buyers.items():
            qty, parsing_errors = parseQuantity(
                str(row[index]), index, buyer, parsing_errors
            )
            if qty == 0:
                continue

            order_line = OrderLine(
                produce=row[headers_dict["produce"]],
                variant=row[headers_dict["variant"]],
                unit=row[headers_dict["unit"]],
                seller=row[headers_dict["seller"]],
                qty=qty,
                buyer=buyer,
            )
            parsing_errors = order_line.setPrice(
                str(row[headers_dict["price"]]), i, parsing_errors
            )
            parsing_errors = order_line.checkErrors(i, parsing_errors)

            order_lines.append(order_line)

    # print(order_lines)
    print(parsing_errors.errors)

    return order_lines, parsing_errors

    orders = orders.replace({np.nan: ""})

    orders = orders.dropna(subset=["Produce Name"])

    if "BUYERS:" not in orders.columns:
        st.error("Error: Missing column 'BUYERS:' in order spreadsheet")
        print("Error: Missing column 'BUYERS:' in order spreadsheet")
        st.stop()

    # Get the names of the buyers that made orders this week
    buyers_column_index = orders.columns.get_loc("BUYERS:") + 1
    # Replace empty string values with 0
    orders.iloc[:, buyers_column_index:] = orders.iloc[:, buyers_column_index:].replace(
        {"": 0}
    )

    # Remove rows where the sum of columns 9 onwards (the buyers area) is equal to 0
    orders = orders.loc[(orders.iloc[:, buyers_column_index:].sum(axis=1) != 0)]
    buyers = orders.columns[buyers_column_index + 1 :][
        orders.iloc[:, buyers_column_index + 1 :].sum() > 0
    ].tolist()

    if not buyers:
        st.success("No buyers this week")
        print("No buyers this week")

    my_order_lines = []

    column_mapping = {
        "Produce Name": "produce",
        "Additional Info": "variant",
        "UNIT": "unit",
        "Price/   UNIT (£)": "price",
        "Growers": "seller",
    }

    keys = list(column_mapping.keys())
    # Check if all keys exist in the columns of orders
    if not set(keys).issubset(set(orders.columns)):
        missing_columns = list(set(keys) - set(orders.columns))
        missing_columns_str = ", ".join(
            missing_columns
        )  # Join the missing columns into a string
        print(f"Error: Missing columns in order spreadsheet: {missing_columns_str}")
        st.error(f"Error: Missing columns in order spreadsheet: {missing_columns_str}")
        st.stop()

    orders = orders.rename(columns=column_mapping)

    print("Order spreadsheet column names are correct")
    st.toast(":white_check_mark: Order spreadsheet column names are correct")

    # Truncate the variant column to 25 characters
    orders["variant"] = orders["variant"].apply(
        lambda x: x[:25] + "..." if len(x) > 25 else x
    )

    non_int_values = orders.loc[
        ~orders["price"].apply(lambda x: isinstance(x, (int, float)))
    ]["price"].tolist()
    if non_int_values:
        if order_sheet_name:
            print(
                f"Non-number only values in price column in {order_sheet_name}: {non_int_values} Please make these numbers only"
            )
            st.error(
                f"Non-number only values in price column in {order_sheet_name}: {non_int_values} Please make these numbers only"
            )
        else:
            print(
                f"Non-number only values in price column: {non_int_values} Please make these numbers only"
            )
            st.error(
                f"Non-number only values in price column: {non_int_values} Please make these numbers only"
            )
        st.stop()

    orders["price"] = orders["price"].astype(float)

    # Multiply the price by 100 to convert to pence
    orders["price"] = orders["price"] * 100
    orders["price"] = orders["price"].astype(int)

    for buyer in buyers:
        # Save the rows that are non-zero for the current buyer
        non_zero_rows = orders.loc[orders[buyer] != 0]

        # Create a new dataframe with the first 8 columns of non_zero_rows and an additional column for orders[buyer]
        buyer_lines = non_zero_rows.iloc[:, :5].copy()
        buyer_lines["qty"] = non_zero_rows[buyer]
        buyer_lines.loc[:, "buyer"] = buyer

        buyer_lines = buyer_lines.to_dict(orient="records")
        for line in buyer_lines:
            my_order_lines.append(line)

    my_order_lines = pd.DataFrame(my_order_lines)

    return my_order_lines


def contacts_formatter(contacts):
    contacts = contacts.replace({np.nan: ""})

    column_mapping = {
        "Buyer Key as in Spreadsheet": "key",
        "Buyer Full Name": "name",
        "Address Line 1": "address1",
        "Address Line 2": "address2",
        "City": "city",
        "Postcode": "postcode",
        "Country": "country",
    }

    keys = list(column_mapping.keys())

    # Check if all keys exist in the columns of orders
    if not set(keys).issubset(set(contacts.columns)):
        missing_columns = list(set(keys) - set(contacts.columns))
        missing_columns_str = ", ".join(
            missing_columns
        )  # Join the missing columns into a string
        print(f"Error: Missing columns in contacts spreadsheet: {missing_columns_str}")
        st.error(
            f"Error: Missing columns in contacts spreadsheet: {missing_columns_str}"
        )
        st.stop()

    contacts = contacts.rename(columns=column_mapping)
    contacts["number"] = ""  # Add a new column called "number" with empty values
    st.toast(":white_check_mark: Contacts column names are correct")
    return contacts


def add_delivery_fee(orders, delivery_fee, no_deliveries):

    return orders


def contacts_checker(contacts, buyers):
    unmatched_buyers = []
    for buyer in buyers:
        if buyer not in contacts.tolist():
            unmatched_buyers.append(buyer)
    if unmatched_buyers:
        st.error(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        print(f"Buyers: {unmatched_buyers} not found in contacts spreadsheet")
        st.stop()
    else:
        st.toast(":white_check_mark: All buyers found in contacts")
        print("All buyers found in contacts")
    return unmatched_buyers


def extract_buyer_list(orders):
    if "BUYERS:" not in orders.columns:
        st.error("Error: Missing column 'BUYERS:' in order spreadsheet")
        print("Error: Missing column 'BUYERS:' in order spreadsheet")
        st.stop()
    buyers_column_index = orders.columns.get_loc("BUYERS:")
    buyers = orders.columns[buyers_column_index + 1 :][
        orders.iloc[:, buyers_column_index + 1 :].sum() > 0
    ].tolist()
    print(f"Buyer list: {buyers}")
    return buyers


def date_extractor(order_sheet):
    try:
        order_sheet_name = str(order_sheet)
        date_str = order_sheet_name.split(" - ")[-1].split(".")[0]
        dateobj = datetime.strptime(date_str, "%d_%m_%Y")
        return dateobj
    except ValueError as e:
        st.error(
            f"Error: Failed to extract date from order sheet: {order_sheet.name}, make sure the file name is in the format '...N - dd_mm_yyyy.xlsx'"
        )
        print(
            f"Error: Failed to extract date from order sheet: {order_sheet.name}, make sure the file name is in the format '...N - dd_mm_yyyy.xlsx"
        )
        st.stop()


if __name__ == "__main__":
    spreadsheet_all = openpyxl.load_workbook("./test.xlsx", data_only=True)
    order_sheet = spreadsheet_all["GROWERS' PAGE"]

    orderify(order_sheet)
