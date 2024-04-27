from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
        if (variant != None):
            variant = (variant[:25] + "..") if len(variant) > 25 else variant
        else:
            variant = " "
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


@dataclass
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
    def __init__(self, date: datetime, buyer: Buyer, lines: list[OrderLine] = []):
        self.date = date
        self.buyer = buyer
        self.lines = lines
    date: datetime
    buyer: Buyer
    lines: list[OrderLine]

    def addLine(self, line: OrderLine):
        self.lines.append(line)

    def toJSON(self):
        if (self.buyer.number == None):
            raise ValueError(
                "Buyer number must be set before converting to JSON")
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
