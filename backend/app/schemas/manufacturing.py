from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class FormulaIngredientBase(BaseModel):
    item_id: int
    sequence: int
    quantity: Decimal
    uom_id: Optional[int] = None
    percentage: Optional[Decimal] = None
    notes: Optional[str] = None


class FormulaIngredientCreate(FormulaIngredientBase):
    pass


class FormulaIngredientResponse(FormulaIngredientBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class FormulaVersionBase(BaseModel):
    batch_size: Decimal
    batch_uom_id: Optional[int] = None
    expected_yield_percent: Decimal = Decimal("100")
    notes: Optional[str] = None
    change_reason: Optional[str] = None


class FormulaVersionCreate(FormulaVersionBase):
    ingredients: List[FormulaIngredientCreate]


class FormulaVersionRevert(BaseModel):
    """Request to revert to a prior formula version. Creates a new version
    that copies the ingredients and settings from the target version."""
    reason: str


class FormulaVersionResponse(FormulaVersionBase):
    id: int
    formula_id: int
    version_number: int
    is_current: bool
    effective_date: Optional[datetime] = None
    change_reason: Optional[str] = None
    reverted_from_version_id: Optional[int] = None
    ingredients: List[FormulaIngredientResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class FormulaBase(BaseModel):
    code: str
    name: str
    product_item_id: int
    description: Optional[str] = None


class FormulaCreate(FormulaBase):
    initial_version: FormulaVersionCreate


class FormulaResponse(FormulaBase):
    id: int
    is_active: bool
    versions: List[FormulaVersionResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ProductionOrderBase(BaseModel):
    formula_id: int
    formula_version_id: int
    planned_quantity: Decimal
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    output_warehouse_id: Optional[int] = None
    output_location_id: Optional[int] = None
    notes: Optional[str] = None


class ProductionOrderCreate(ProductionOrderBase):
    pass


class ProductionOrderUpdate(BaseModel):
    status: Optional[str] = None
    actual_quantity: Optional[Decimal] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    notes: Optional[str] = None


class ProductionConsumptionCreate(BaseModel):
    item_id: int
    lot_id: int
    actual_quantity: Decimal


class ProductionOutputCreate(BaseModel):
    lot_number: str
    quantity: Decimal
    warehouse_id: Optional[int] = None
    location_id: Optional[int] = None


class ProductionOrderResponse(ProductionOrderBase):
    id: int
    order_number: str
    status: str
    actual_quantity: Optional[Decimal] = None
    yield_percent: Optional[Decimal] = None
    output_lot_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
