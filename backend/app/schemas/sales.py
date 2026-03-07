from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CustomerBase(BaseModel):
    code: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    payment_terms: Optional[str] = None
    tax_exempt: bool = False


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SalesOrderLineBase(BaseModel):
    item_id: int
    line_number: int
    quantity_ordered: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0")


class SalesOrderLineCreate(SalesOrderLineBase):
    pass


class SalesOrderLineResponse(SalesOrderLineBase):
    id: int
    quantity_shipped: Decimal
    line_total: Decimal
    allocated_lot_id: Optional[int] = None

    class Config:
        from_attributes = True


class SalesOrderBase(BaseModel):
    customer_id: int
    requested_ship_date: Optional[datetime] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class SalesOrderCreate(SalesOrderBase):
    lines: List[SalesOrderLineCreate]


class SalesOrderUpdate(BaseModel):
    status: Optional[str] = None
    requested_ship_date: Optional[datetime] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None


class SalesOrderResponse(SalesOrderBase):
    id: int
    order_number: str
    order_date: datetime
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    lines: List[SalesOrderLineResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ShipmentCreate(BaseModel):
    sales_order_id: int
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    lines: List[dict]  # [{sales_order_line_id, lot_id, quantity_shipped}]


class ShipmentResponse(BaseModel):
    id: int
    shipment_number: str
    sales_order_id: int
    ship_date: datetime
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
