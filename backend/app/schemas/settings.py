from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# --- Ship Via ---

class ShipViaBase(BaseModel):
    name: str
    carrier: Optional[str] = None
    account_number: Optional[str] = None


class ShipViaCreate(ShipViaBase):
    pass


class ShipViaUpdate(BaseModel):
    name: Optional[str] = None
    carrier: Optional[str] = None
    account_number: Optional[str] = None
    is_active: Optional[bool] = None


class ShipViaResponse(ShipViaBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Branding ---

class BrandingBase(BaseModel):
    company_name: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    primary_color: str = "#1e40af"


class BrandingUpdate(BrandingBase):
    company_name: Optional[str] = None


class BrandingResponse(BrandingBase):
    id: int
    logo_path: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Price List ---

class PriceListBase(BaseModel):
    item_id: int
    price_type: str  # customer, vendor
    entity_id: int
    unit_price: Decimal
    min_quantity: Decimal = Decimal("0")
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class PriceListCreate(PriceListBase):
    pass


class PriceListUpdate(BaseModel):
    unit_price: Optional[Decimal] = None
    min_quantity: Optional[Decimal] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class PriceListResponse(PriceListBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    id: int
    item_id: int
    price_type: str
    entity_id: int
    old_price: Optional[Decimal] = None
    new_price: Decimal
    changed_at: datetime
    changed_by: Optional[int] = None

    class Config:
        from_attributes = True


# --- Ship To ---

class ShipToBase(BaseModel):
    name: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    is_default: bool = False


class ShipToCreate(ShipToBase):
    customer_id: int


class ShipToUpdate(BaseModel):
    name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ShipToResponse(ShipToBase):
    id: int
    customer_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
