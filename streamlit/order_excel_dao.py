import re
from datetime import datetime
import openpyxl.workbook
import openpyxl.worksheet
import openpyxl.worksheet.worksheet
import openpyxl
import numpy as np
from domain import ValidationError, Buyer, ValidationReport, Order, Seller, MarketPlace, MarketPlaceImport
import streamlit as st


class ExcelCoords:
    row: int
    col: int
    _A = ord("A")

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col

    def __str__(self):
        col_letter = chr(self._A + self.col)
        return f"{col_letter}{self.row}"


# def load(file_path: str) -> MarketPlaceImport:

class ExcelParser:
    """Parse an excel file"""

    validation_errors: list[ValidationError] = []

    def _load_worksheet_from_excel(
            self,
            excel_file,
            worksheet_name: str) -> openpyxl.worksheet.worksheet:
        """Gets the worksheet from the workbook

        Args:
            excel_file (UploadedFile): The uploaded file
            sheet_name (str): Name of sheet to get from workbook

        Returns:
            Worksheet: The worksheet
        """
        workbook = openpyxl.load_workbook(
            excel_file, data_only=True)
        try:
            worksheet = workbook[worksheet_name]
        except KeyError:
            st.error("Expected GROWERS' PAGE worksheet, but it does not exist.")
            self.validation_errors.append(
                ValidationError(
                    f"Expected {worksheet_name} worksheet, but it does not exist.")
            )
            raise KeyError(
                f"Expected {worksheet_name} worksheet, but it does not exist."
            )
        return worksheet

    def _date_extractor(self, file_name: str) -> datetime:
        try:
            order_sheet_name = str(file_name)
            date_str = order_sheet_name.split(" - ")[-1].split(".")[0]
            dateobj = datetime.strptime(date_str, "%d_%m_%Y")
            return dateobj
        except ValueError:
            self.validation_errors.append(
                ValidationError(
                    f"Failed to extract date from order sheet: {file_name}, make sure the file name is in the format '...N - dd_mm_yyyy.xlsx")
            )

    def _reset_errors(self):
        self.validation_errors = []


class OrderExcelParser(ExcelParser):
    """
    Will parse the order sheet
    """
    buyers: list[Buyer]
    _header_row = 3
    VAT_RATE = 0.0

    def __init__(self, buyers: list[Buyer]):
        self.buyers = buyers

    def _find_buyer(self, name: str) -> Buyer:
        for buyer in self.buyers:
            if buyer.key == name:
                return buyer
        return None

    def _parse_order_headers(
        self,
        order_sheet: openpyxl.worksheet.worksheet.Worksheet,
    ) -> tuple[dict[str, int], dict[int, Buyer]]:
        """Parse the headers of the order sheet

        Args:
            headers (list): The headers of the order sheet

        Returns:
            tuple[dict[str, int], dict[int, str]]: A tuple containing the header
            dictionary and the buyer keys
        """

        headers = order_sheet[self._header_row]
        headers = [cell.value for cell in headers]

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
                self.validation_errors.append(
                    ValidationError(
                        f"Header {key} could not be found in the sheet.")
                )

            header_dict[value] = index_of_header

        buyer_index = headers.index("BUYERS:")
        i = buyer_index + 1
        end = len(headers)

        contact_list = [buyer.key for buyer in self.buyers]

        for i in range(i, end):
            current_buyer = headers[i]

            if i > 100:
                self.validation_errors.append(ValidationError(
                    """It looks like there were lots of buyers, check
                    that any headers without buyers are empty"""
                ))

            if current_buyer is None or current_buyer == "":
                continue

            current_buyer = str(current_buyer).strip()

            if current_buyer not in contact_list:
                self.validation_errors.append(
                    ValidationError(
                        f"Buyer {current_buyer} not found in contacts sheet.")
                )

            current_buyer_object = self._find_buyer(current_buyer)

            buyer_keys[i] = current_buyer_object

        return header_dict, buyer_keys

    def _parse_quantity(self, quantity: str, coords: ExcelCoords) -> float:
        """Parses the quantity from the row

        Args:
            row (tuple): The row to parse
            headers_dict (dict[str, int]): The headers dictionary

        Returns:
            float: The quantity
        """
        cleaned = re.sub(r"[^0-9\.]", "", str(quantity))
        float_quantity = 0.0
        try:
            float_quantity = float(cleaned)
        except ValueError:
            self.validation_errors.append(
                ValidationError(f"Quantity at {coords} could not be parsed."))

        return float_quantity

    def _parse_price(self, price: str, coords: ExcelCoords) -> int:
        """Parse the price from string using regex etc.

        Args:
            price (str): Price as string from sheet
            row (int): The row number

        Returns:
            int: The price as an integer (0 if failed to parse)
        """
        cleaned = re.sub(r"[^0-9\.]", "", str(price))
        try:
            float_price = float(cleaned)
        except ValueError:
            self.validation_errors.append(
                ValidationError(f"Price at {coords} could not be parsed."))
            return 0

        rounded = np.round(float_price * 100, decimals=0)

        try:
            return int(rounded)
        except ValueError:
            self.validation_errors.append(
                ValidationError(
                    f"""Price could not be parsed at {coords},
                    check that it has only 2 decimal places."""
                )
            )
            return 0

    def _parse_orders(
        self,
        order_sheet: openpyxl.worksheet.worksheet.Worksheet,
        headers_dict: dict[str, int],
        buyers: dict[int, Buyer],
        delivery_date: str,
        name: str
    ) -> list[Order]:
        """_summary_

        Args:
            order_sheet (openpyxl.worksheet.worksheet.Worksheet): _description_
            headers_dict (dict[str, int]): _description_
            buyers (dict[int, str]): _description_
            delivery_date (str): _description_

        Returns:
            list[Order]: _description_
        """
        i = self._header_row

        orders: list[Order] = []

        seller_set: set[Seller] = set()

        for row in order_sheet.iter_rows(min_row=self._header_row+1, values_only=True):
            i += 1

            if row[headers_dict["price"]] is None or row[headers_dict["price"]] == "":
                continue

            price = self._parse_price(row[headers_dict["price"]],
                                      ExcelCoords(row=i, col=headers_dict["price"]))

            for index, buyer in buyers.items():
                quantity = self._parse_quantity(
                    row[index], ExcelCoords(row=i, col=index))

                if quantity == 0:
                    continue

                seller_name = str(row[headers_dict["seller"]]).strip()
                produce = row[headers_dict["produce"]]
                variant = row[headers_dict["variant"]]
                unit = row[headers_dict["unit"]]
                vat_rate = self.VAT_RATE

                orders.append(
                    Order(
                        produce=produce,
                        variant=variant,
                        unit=unit,
                        seller=Seller(seller_name),
                        buyer=buyer,
                        price=price,
                        quantity=quantity,
                        vat_rate=vat_rate,
                        order_date=delivery_date
                    )
                )

                seller_set.add(Seller(seller_name))

        week_number = self._parse_week(name)

        market_place = MarketPlace(
            sellers=frozenset(seller_set),
            buyers=frozenset(self.buyers),
            orders=frozenset(orders),
            week=week_number
        )

        return market_place

    def _parse_week(self, order_sheet_name: str) -> int:
        """
        Parses the week number from the order sheet
        """
        week_number_match = re.search(r"k (\d+)", order_sheet_name)
        if week_number_match:
            week_number = week_number_match.group(1)
        else:
            st.error("""Invalid order sheet name.
                     Please use the format: OxFarmToFork spreadsheet week N - DD_MM_YYYY.xlsx""")

        return week_number

    def parse(self, file, delivery_date, use_file_name_for_date=False) -> MarketPlaceImport:
        """
        Parses order data from the spreadsheet to a clean domain
        """
        # Reset errors
        self._reset_errors()
        order_sheet = self._load_worksheet_from_excel(file, "GROWERS' PAGE")
        headers_dict, buyers = self._parse_order_headers(order_sheet)
        if use_file_name_for_date:
            delivery_date = self._date_extractor(file.name)
        market_place = self._parse_orders(
            order_sheet, headers_dict, buyers, delivery_date, file.name)
        validation_report = ValidationReport(
            source=file.name, errors=self.validation_errors)
        return MarketPlaceImport(
            market_place=market_place,
            validation_report=validation_report
        )
