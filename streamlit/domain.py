# this 

@dataclass(frozen=True)
class Buyer:
    name: str
    key: str
    address_line_1: str
    city: str
    postcode: str
    country: str
    number: Optional[str] = None
    address_line_2: Optional[str] = None


@dataclass(frozen=True)
class DeliveryNote:
    date: date
    buyer: Buyer
    orders: frozenset[Order]


@dataclass(frozen=True)
class Invoice:
    date: date
    buyer: Buyer
    due_date: date
    reference: str
    orders: frozenset[Order]

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
    date: Optional[datetime] = None

@dataclass(frozen=True)
class MarketPlace:
    sellers: frozenset[Seller]
    buyers: frozenset[Buyer]
    orders: frozenset[Order]

@dataclass(frozen=True)
class ValidationError:
    # error check functions will set in here, the UI will sit in functions

@dataclass(frozen=True)
class ValidationReport:
    errors: list[ValidationError]

@dataclass(frozen=True)
class MarketPlaceImport:
    market_place: MarketPlace
    validation_report: ValidationReport
