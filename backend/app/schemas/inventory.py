from pydantic import BaseModel
from typing import Optional, List
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
    tracking_type: str = "inventory_lot"
    max_shelf_life_days: Optional[int] = None
    does_not_expire: bool = False
    target_min_qty: Optional[Decimal] = None
    master_recipe_id: Optional[int] = None
    replacement_cost: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    preferred_supplier_id: Optional[int] = None
    specific_gravity: Optional[Decimal] = None
    density_lb_gal: Optional[Decimal] = None
    voc_percent: Optional[Decimal] = None
    boiling_point: Optional[str] = None
    flash_point: Optional[str] = None


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
    tracking_type: Optional[str] = None
    max_shelf_life_days: Optional[int] = None
    does_not_expire: Optional[bool] = None
    target_min_qty: Optional[Decimal] = None
    master_recipe_id: Optional[int] = None
    replacement_cost: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    preferred_supplier_id: Optional[int] = None
    specific_gravity: Optional[Decimal] = None
    density_lb_gal: Optional[Decimal] = None
    voc_percent: Optional[Decimal] = None
    boiling_point: Optional[str] = None
    flash_point: Optional[str] = None


class ItemResponse(ItemBase):
    id: int
    is_active: bool
    current_fifo_cost: Optional[Decimal] = None
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


# --- Item Aliases ---

class ItemAliasBase(BaseModel):
    alias_code: str
    alias_name: Optional[str] = None
    alias_type: Optional[str] = None  # customer, vendor, internal, regulatory, legacy
    reference_id: Optional[int] = None
    notes: Optional[str] = None


class ItemAliasCreate(ItemAliasBase):
    pass


class ItemAliasUpdate(BaseModel):
    alias_code: Optional[str] = None
    alias_name: Optional[str] = None
    alias_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ItemAliasResponse(ItemAliasBase):
    id: int
    item_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Pack Extensions ---

class PackComponentBase(BaseModel):
    component_item_id: int
    quantity: Decimal
    sequence: int = 0
    uom_id: Optional[int] = None
    notes: Optional[str] = None


class PackComponentCreate(PackComponentBase):
    pass


class PackComponentResponse(PackComponentBase):
    id: int
    pack_item_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PackDefinitionCreate(BaseModel):
    """Create or replace the full pack definition for an item."""
    components: List[PackComponentCreate]


class PackOperationRequest(BaseModel):
    """Request to pack or unpack items (creates/consumes inventory)."""
    pack_item_id: int
    quantity: Decimal  # number of packs to assemble or disassemble
    warehouse_id: Optional[int] = None
    location_id: Optional[int] = None
    lot_number: Optional[str] = None  # for pack output lot
    component_lots: Optional[List[dict]] = None  # [{component_item_id, lot_id}] for packing


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


# --- Item Active Recipes ---

class ItemActiveRecipeCreate(BaseModel):
    formula_id: int
    is_master: bool = False


class ItemActiveRecipeResponse(BaseModel):
    id: int
    item_id: int
    formula_id: int
    is_master: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- QC Test Definitions (Settings) ---

class QCTestDefinitionBase(BaseModel):
    name: str
    test_type: str  # pass_fail, range
    method: Optional[str] = None
    uom: Optional[str] = None


class QCTestDefinitionCreate(QCTestDefinitionBase):
    pass


class QCTestDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    test_type: Optional[str] = None
    method: Optional[str] = None
    uom: Optional[str] = None
    is_active: Optional[bool] = None


class QCTestDefinitionResponse(QCTestDefinitionBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Item QC Test Assignments ---

class ItemQCTestCreate(BaseModel):
    qc_test_definition_id: int
    target_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None


class ItemQCTestResponse(BaseModel):
    id: int
    item_id: int
    qc_test_definition_id: int
    target_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Pack Extension Definitions (Settings) ---

class PackExtensionMaterialBase(BaseModel):
    material_item_id: int
    quantity_per_lb: Decimal
    uom_id: Optional[int] = None


class PackExtensionMaterialCreate(PackExtensionMaterialBase):
    pass


class PackExtensionMaterialResponse(PackExtensionMaterialBase):
    id: int
    pack_extension_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PackExtensionDefinitionBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class PackExtensionDefinitionCreate(PackExtensionDefinitionBase):
    materials: List[PackExtensionMaterialCreate] = []


class PackExtensionDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    materials: Optional[List[PackExtensionMaterialCreate]] = None


class PackExtensionDefinitionResponse(PackExtensionDefinitionBase):
    id: int
    is_active: bool
    materials: List[PackExtensionMaterialResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Item Pack Extension Assignments ---

class ItemPackExtensionCreate(BaseModel):
    pack_extension_id: int
    desired_fill_amount: Optional[Decimal] = None
    fill_uom_id: Optional[int] = None


class ItemPackExtensionUpdate(BaseModel):
    desired_fill_amount: Optional[Decimal] = None
    fill_uom_id: Optional[int] = None


class ItemPackExtensionResponse(BaseModel):
    id: int
    item_id: int
    pack_extension_id: int
    desired_fill_amount: Optional[Decimal] = None
    fill_uom_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
