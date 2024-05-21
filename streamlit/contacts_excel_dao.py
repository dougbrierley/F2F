"""
Module to upload the contacts to buyers
"""
from domain import ValidationError, Buyer, ContactsImport, ValidationReport
from openpyxl.worksheet.worksheet import Worksheet
from order_excel_dao import ExcelParser
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class _PropertyExcelColumnIndexes:
    buyer_key: Optional[int]
    buyer_full_name: Optional[int]
    address_line_1: Optional[int]
    address_line_2: Optional[int]
    city: Optional[int]
    postcode: Optional[int]
    country: Optional[int]


class ContactsExcelParser(ExcelParser):
    """
    class to create the buyer objects from the contacts spreadsheet
    """
    _header_row = 1

    def retrieve_property_name_excel_column_indexes(
            self,
            contacts_sheet: Worksheet
    ) -> _PropertyExcelColumnIndexes:
        "Load in and validate the headers"

        headers = tuple(cell.value for cell in contacts_sheet[self._header_row])

        def retrieve_column_index(excel_header_name: str) -> Optional[int]:
            try:
                return headers.index(excel_header_name)
            except ValueError:
                self.validation_errors.append(
                    ValidationError(
                        f"Header {excel_header_name} could not be found in the contacts sheet.")
                )

        return _PropertyExcelColumnIndexes(
            buyer_key=retrieve_column_index("Buyer Key as in Spreadsheet"),
            buyer_full_name=retrieve_column_index("Buyer Full Name"),
            address_line_1=retrieve_column_index("Address Line 1"),
            address_line_2=retrieve_column_index("Address Line 2"),
            city=retrieve_column_index("City"),
            postcode=retrieve_column_index("Postcode"),
            country=retrieve_column_index("Country"),
        )

    def _load_cell(self, row: tuple, key: int, row_number: int, can_be_null: bool = True) -> str:
        """
        Load the row from the contacts sheet
        """
        try:
            item = row[key]
        except IndexError:
            return ""
        if (item is None or item == "") and can_be_null is False:
            self.validation_errors.append(
                ValidationError(
                    f"Row {row_number} and item {key} is empty and should not be."
                )
            )
            return ""
        if item is None:
            return ""
        return item

    def _contacts_parser(
            self,
            contacts_sheet: Worksheet,
            property_excel_column_indexes: _PropertyExcelColumnIndexes,
    ) -> frozenset[Buyer]:
        """
        This function takes in the contacts dataframe and returns a
        list of all the buyers.
        """

        buyers: list[Buyer] = []

        row_number = self._header_row - 1

        for row in contacts_sheet.iter_rows(min_row=self._header_row + 1, values_only=True):
            row_number = row_number + 1

            # Skip rows that do not have a buyer
            if row[property_excel_column_indexes.buyer_key] is None or row[
                property_excel_column_indexes.buyer_full_name] == "": #Weak condition
                continue

            buyers.append(Buyer(
                key=self._load_cell(
                    row, property_excel_column_indexes.buyer_key, row_number, can_be_null=False),
                name=self._load_cell(
                    row, property_name_to_excel_column_index["buyer_full_name"], row_number, can_be_null=False),
                address_line_1=self._load_cell(
                    row, property_name_to_excel_column_index["address_line_1"], row_number, can_be_null=False),
                city=self._load_cell(
                    row, property_name_to_excel_column_index["city"], row_number, can_be_null=False),
                postcode=self._load_cell(
                    row, property_name_to_excel_column_index["postcode"], row_number, can_be_null=False),
                country=self._load_cell(
                    row, property_name_to_excel_column_index["country"], row_number, can_be_null=True),
                address_line_2=self._load_cell(
                    row, property_name_to_excel_column_index["address_line_2"], row_number, can_be_null=True)
            ))

        return frozenset(buyers)

    def parse(self, file) -> ContactsImport:
        """"
        Takes the contacts file path and returns the buyers with all their information
        """
        self._reset_errors()
        contacts_sheet = self._load_worksheet_from_excel(file, "Contacts")

        buyers = self._contacts_parser(contacts_sheet,
                                       property_excel_column_indexes=self.retrieve_property_name_excel_column_indexes(
                                           contacts_sheet))
        contacts_validation_report = ValidationReport(file.name, self.validation_errors)
        return ContactsImport(buyers, contacts_validation_report)
