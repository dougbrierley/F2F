"""
Module to upload the contacts to buyers
"""
from domain import ValidationError, Buyer, ContactsImport, ValidationReport
from openpyxl.worksheet.worksheet import Worksheet
from order_excel_dao import ExcelParser


class ContactsExcelParser(ExcelParser):
    """
    class to create the buyer objects from the contacts spreadsheet
    """
    _header_row = 1

    def _parse_headers(
            self,
            contacts_sheet: Worksheet
    ) -> tuple[dict[str, int], dict[int, str], list[ValidationError]]:
        "Load in and validate the headers"

        headers = contacts_sheet[self._header_row]
        headers = [cell.value for cell in headers]

        column_mapping = {
            "Buyer Key as in Spreadsheet": "buyer_key",
            "Buyer Full Name": "buyer_full_name",
            "Address Line 1": "address_line_1",
            "Address Line 2": "address_line_2",
            "City": "city",
            "Postcode": "postcode",
            "Country": "country",
        }

        contact_header_dict = {
            "buyer_key": None,
            "buyer_full_name": None,
            "address_line_1": None,
            "address_line_2": None,
            "city": None,
            "postcode": None,
            "country": None,
        }

        for key, value in column_mapping.items():
            try:
                index_of_header = headers.index(key)

            except ValueError:
                self.validation_errors.append(
                    ValidationError(
                        f"Header {key} could not be found in the contacts sheet.")
                )

            contact_header_dict[value] = index_of_header

        return contact_header_dict

    def _load_cell(self, row: tuple, key: int, row_number: int, can_be_null: bool = True) -> str:
        """
        Load the row from the contacts sheet
        """
        try:
            item = row[key]
            item = str(item).strip()
        except IndexError:
            return ""
        if (item is None or item == "") and can_be_null is False:
            self.validation_errors.append(
                ValidationError(
                    f"Row {row_number} and item {key} is empty and should not be."
                )
            )
            return ""
        if item is None or item == "None":
            return ""
        return item

    def _contacts_parser(
        self,
        contacts_sheet: Worksheet,
        headers_dict: dict[str, int],
    ) -> tuple[list[Buyer], list[ValidationError]]:
        """
        This function takes in the contacts dataframe and returns a
        list of all the buyers.
        """

        buyers: list[Buyer] = []

        row_number = self._header_row - 1

        for row in contacts_sheet.iter_rows(min_row=self._header_row + 1, values_only=True):
            row_number = row_number + 1

            # Skip rows that do not have a buyer
            if row[headers_dict["buyer_key"]] is None or row[headers_dict["buyer_full_name"]] == "":
                continue
            
            buyer = Buyer(
                key=self._load_cell(
                    row, headers_dict["buyer_key"], row_number, can_be_null=False),
                name=self._load_cell(
                    row, headers_dict["buyer_full_name"], row_number, can_be_null=False),
                address_line_1=self._load_cell(
                    row, headers_dict["address_line_1"], row_number, can_be_null=False),
                city=self._load_cell(
                    row, headers_dict["city"], row_number, can_be_null=False),
                postcode=self._load_cell(
                    row, headers_dict["postcode"], row_number, can_be_null=False),
                country=self._load_cell(
                    row, headers_dict["country"], row_number, can_be_null=True),
                address_line_2=self._load_cell(
                    row, headers_dict["address_line_2"], row_number, can_be_null=True)
            )

            buyers.append(buyer)

        return buyers

    def parse(self, file) -> ContactsImport:
        """"
        Takes the contacts file path and returns the buyers with all their information
        """
        self._reset_errors()
        contacts_sheet = self._load_worksheet_from_excel(file, "Contacts")
        headers_index = self._parse_headers(contacts_sheet)
        buyers = self._contacts_parser(contacts_sheet, headers_index)
        contacts_validation_report = ValidationReport(
            file.name, self.validation_errors)
        contacts_import = ContactsImport(buyers, contacts_validation_report)
        return contacts_import
