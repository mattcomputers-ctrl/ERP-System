from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# --- Recipe Ingredients ---

class RecipeIngredientCreate(BaseModel):
    item_id: int
    sequence: int
    weight_percent: Decimal
    notes: Optional[str] = None


class RecipeIngredientResponse(RecipeIngredientCreate):
    id: int

    class Config:
        from_attributes = True


# --- Recipe Procedure Steps ---

class RecipeProcedureStepCreate(BaseModel):
    sequence: int
    step_type: str  # add_ingredient, instruction
    ingredient_item_id: Optional[int] = None  # for add_ingredient steps
    instruction_text: Optional[str] = None


class RecipeProcedureStepResponse(RecipeProcedureStepCreate):
    id: int

    class Config:
        from_attributes = True


# --- Recipe Versions ---

class RecipeVersionCreate(BaseModel):
    comment: Optional[str] = None
    batch_size: Optional[Decimal] = None
    batch_uom_id: Optional[int] = None
    expected_yield_percent: Decimal = Decimal("100")
    ingredients: List[RecipeIngredientCreate] = []
    procedure_steps: List[RecipeProcedureStepCreate] = []


class RecipeVersionResponse(BaseModel):
    id: int
    recipe_id: int
    version_number: int
    status: str
    comment: Optional[str] = None
    batch_size: Optional[Decimal] = None
    batch_uom_id: Optional[int] = None
    expected_yield_percent: Decimal
    published_at: Optional[datetime] = None
    created_at: datetime
    ingredients: List[RecipeIngredientResponse] = []
    procedure_steps: List[RecipeProcedureStepResponse] = []

    class Config:
        from_attributes = True


# --- Recipes ---

class RecipeCreate(BaseModel):
    product_item_id: int
    description: Optional[str] = None
    initial_version: RecipeVersionCreate


class RecipeUpdate(BaseModel):
    description: Optional[str] = None


class RecipeResponse(BaseModel):
    id: int
    product_item_id: int
    description: Optional[str] = None
    is_active: bool
    versions: List[RecipeVersionResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Batch Ticket Packages ---

class BatchTicketPackageCreate(BaseModel):
    pack_extension_id: int
    quantity: Decimal


class BatchTicketPackageResponse(BatchTicketPackageCreate):
    id: int

    class Config:
        from_attributes = True


# --- Batch Ticket Materials ---

class BatchTicketMaterialResponse(BaseModel):
    id: int
    item_id: int
    planned_quantity: Decimal
    available_quantity: Optional[Decimal] = None
    has_shortage: bool

    class Config:
        from_attributes = True


# --- Batch Tickets ---

class BatchTicketCreate(BaseModel):
    ticket_type: str  # batch, repack
    recipe_id: Optional[int] = None
    recipe_version_id: Optional[int] = None
    item_id: int
    planned_quantity: Decimal
    due_date: Optional[datetime] = None
    customer_id: Optional[int] = None
    shortage_override: bool = False
    notes: Optional[str] = None
    packages: List[BatchTicketPackageCreate] = []


class BatchTicketUpdate(BaseModel):
    status: Optional[str] = None
    planned_quantity: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    customer_id: Optional[int] = None
    shortage_override: Optional[bool] = None
    notes: Optional[str] = None


class BatchTicketResponse(BaseModel):
    id: int
    ticket_number: str
    ticket_type: str
    recipe_id: Optional[int] = None
    recipe_version_id: Optional[int] = None
    item_id: int
    planned_quantity: Decimal
    due_date: Optional[datetime] = None
    customer_id: Optional[int] = None
    status: str
    has_shortage: bool
    shortage_override: bool
    shortage_details: Optional[str] = None
    notes: Optional[str] = None
    packages: List[BatchTicketPackageResponse] = []
    planned_materials: List[BatchTicketMaterialResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Batch Execution ---

class BatchExecutionConsumptionCreate(BaseModel):
    item_id: int
    lot_id: int
    actual_quantity: Decimal


class BatchExecutionOutputCreate(BaseModel):
    lot_number: str
    quantity: Decimal
    warehouse_id: Optional[int] = None


class BatchExecutionConsumptionResponse(BaseModel):
    id: int
    item_id: int
    lot_id: Optional[int] = None
    planned_quantity: Optional[Decimal] = None
    actual_quantity: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None

    class Config:
        from_attributes = True


class BatchExecutionOutputResponse(BaseModel):
    id: int
    item_id: int
    lot_id: Optional[int] = None
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None

    class Config:
        from_attributes = True


class BatchExecutionQCResultCreate(BaseModel):
    qc_test_definition_id: int
    target_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    result_value: Optional[Decimal] = None
    result_text: Optional[str] = None
    passed: Optional[bool] = None
    notes: Optional[str] = None


class BatchExecutionQCResultResponse(BaseModel):
    id: int
    execution_id: int
    qc_test_definition_id: int
    target_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    result_value: Optional[Decimal] = None
    result_text: Optional[str] = None
    passed: Optional[bool] = None
    tested_by: Optional[int] = None
    tested_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class BatchExecutionQCRequest(BaseModel):
    results: List[BatchExecutionQCResultCreate]


class BatchExecutionResponse(BaseModel):
    id: int
    batch_ticket_id: int
    status: str
    actual_yield: Optional[Decimal] = None
    yield_percent: Optional[Decimal] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    consumptions: List[BatchExecutionConsumptionResponse] = []
    outputs: List[BatchExecutionOutputResponse] = []
    qc_results: List[BatchExecutionQCResultResponse] = []

    class Config:
        from_attributes = True


class BatchExecutionStart(BaseModel):
    notes: Optional[str] = None


class BatchExecutionConsumeRequest(BaseModel):
    consumptions: List[BatchExecutionConsumptionCreate]


class BatchExecutionCompleteRequest(BaseModel):
    output: BatchExecutionOutputCreate
    notes: Optional[str] = None
