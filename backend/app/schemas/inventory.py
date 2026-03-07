from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ItemBase(BaseModel):
    item_code: str
    name: str
    description: Optional[str] = None
    item_type: str
    gl_group_id: Optional[int] = None
    primary_uom_id: Optional[int] = None
    reorder_level: Optional[Decimal] = None
    safety_stock: Optional[Decimal] = None
    is_lot_tracked: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    gl_group_id: Optional[int] = None
    primary_uom_id: Optional[int] = None
    reorder_level: Optional[Decimal] = None
    safety_stock: Optional[Decimal] = None
    is_lot_tracked: Optional[bool] = None
    is_active: Optional[bool] = None


class ItemResponse(ItemBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WarehouseBase(BaseModel):
    code: str
    name: str
    address: Optional[str] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseResponse(WarehouseBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class LocationBase(BaseModel):
    warehouse_id: int
    code: str
    name: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class LotBase(BaseModel):
    lot_number: str
    item_id: int
    warehouse_id: Optional[int] = None
    location_id: Optional[int] = None


class LotCreate(LotBase):
    quantity_on_hand: Decimal = Decimal("0")
    vendor_lot_number: Optional[str] = None
    expiration_date: Optional[datetime] = None
    notes: Optional[str] = None


class LotResponse(LotBase):
    id: int
    quantity_on_hand: Decimal
    quantity_allocated: Decimal
    quantity_on_hold: Decimal
    status: str
    expiration_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    vendor_lot_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryAdjustment(BaseModel):
    item_id: int
    lot_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    reason: Optional[str] = None


class InventoryTransfer(BaseModel):
    item_id: int
    lot_id: int
    from_warehouse_id: int
    from_location_id: Optional[int] = None
    to_warehouse_id: int
    to_location_id: Optional[int] = None
    quantity: Decimal


class InventoryTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    item_id: int
    lot_id: Optional[int] = None
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UOMBase(BaseModel):
    name: str
    abbreviation: str
    category: str


class UOMCreate(UOMBase):
    pass


class UOMResponse(UOMBase):
    id: int

    class Config:
        from_attributes = True
