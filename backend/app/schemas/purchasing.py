from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class VendorBase(BaseModel):
    code: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # Office address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    # Remit-to address
    remit_address_line1: Optional[str] = None
    remit_address_line2: Optional[str] = None
    remit_city: Optional[str] = None
    remit_state: Optional[str] = None
    remit_postal_code: Optional[str] = None
    remit_country: str = "US"
    payment_terms: Optional[str] = None
    default_ship_via_id: Optional[int] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    remit_address_line1: Optional[str] = None
    remit_address_line2: Optional[str] = None
    remit_city: Optional[str] = None
    remit_state: Optional[str] = None
    remit_postal_code: Optional[str] = None
    remit_country: Optional[str] = None
    payment_terms: Optional[str] = None
    default_ship_via_id: Optional[int] = None
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class POLineBase(BaseModel):
    item_id: int
    line_number: int
    quantity_ordered: Decimal
    unit_price: Decimal


class POLineCreate(POLineBase):
    pass


class POLineResponse(POLineBase):
    id: int
    quantity_received: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class PurchaseOrderBase(BaseModel):
    vendor_id: int
    ship_via_id: Optional[int] = None
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    lines: List[POLineCreate]


class PurchaseOrderUpdate(BaseModel):
    status: Optional[str] = None
    ship_via_id: Optional[int] = None
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    po_number: str
    order_date: datetime
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    lines: List[POLineResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ReceiptLineCreate(BaseModel):
    purchase_order_line_id: int
    item_id: int
    lot_number: str
    quantity_received: Decimal
    warehouse_id: Optional[int] = None
    location_id: Optional[int] = None
    vendor_lot_number: Optional[str] = None
    expiration_date: Optional[datetime] = None
    qc_hold: bool = False


class ReceiptCreate(BaseModel):
    purchase_order_id: int
    notes: Optional[str] = None
    lines: List[ReceiptLineCreate]


class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    purchase_order_id: int
    receipt_date: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
