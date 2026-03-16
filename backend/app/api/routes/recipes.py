from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.recipes import (
    Recipe, RecipeVersion, RecipeIngredient, RecipeProcedureStep,
    BatchTicket, BatchTicketPackage, BatchTicketMaterial,
    BatchExecution, BatchExecutionConsumption, BatchExecutionOutput,
)
from app.models.inventory import Item, Lot, InventoryTransaction, FIFOCostLayer
from app.schemas.recipes import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeVersionCreate, RecipeVersionResponse,
    BatchTicketCreate, BatchTicketUpdate, BatchTicketResponse,
    BatchExecutionStart, BatchExecutionConsumeRequest, BatchExecutionCompleteRequest,
    BatchExecutionResponse,
)

router = APIRouter(prefix="/recipes", tags=["Recipes"])


# ===== RECIPES =====

@router.get("/", response_model=List[RecipeResponse])
def list_recipes(
    product_item_id: Optional[int] = None,
    current_user=Depends(require_permission("manufacturing", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Recipe).filter(Recipe.is_active == True)
    if product_item_id:
        q = q.filter(Recipe.product_item_id == product_item_id)
    return q.all()


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    r_in: RecipeCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == r_in.product_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Product item not found")
    recipe = Recipe(
        product_item_id=r_in.product_item_id,
        description=r_in.description,
    )
    version = RecipeVersion(
        version_number=1,
        status="draft",
        comment=r_in.initial_version.comment,
        batch_size=r_in.initial_version.batch_size,
        batch_uom_id=r_in.initial_version.batch_uom_id,
        expected_yield_percent=r_in.initial_version.expected_yield_percent,
    )
    for ing in r_in.initial_version.ingredients:
        version.ingredients.append(RecipeIngredient(**ing.model_dump()))
    for step in r_in.initial_version.procedure_steps:
        version.procedure_steps.append(RecipeProcedureStep(**step.model_dump()))
    recipe.versions.append(version)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int, r_in: RecipeUpdate,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    for k, v in r_in.model_dump(exclude_unset=True).items():
        setattr(recipe, k, v)
    db.commit()
    db.refresh(recipe)
    return recipe


# --- Recipe Versions ---

@router.post("/{recipe_id}/versions", response_model=RecipeVersionResponse)
def add_recipe_version(
    recipe_id: int, v_in: RecipeVersionCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    max_ver = db.query(sa_func.max(RecipeVersion.version_number)).filter(
        RecipeVersion.recipe_id == recipe_id
    ).scalar() or 0
    version = RecipeVersion(
        recipe_id=recipe_id,
        version_number=max_ver + 1,
        status="draft",
        comment=v_in.comment,
        batch_size=v_in.batch_size,
        batch_uom_id=v_in.batch_uom_id,
        expected_yield_percent=v_in.expected_yield_percent,
    )
    for ing in v_in.ingredients:
        version.ingredients.append(RecipeIngredient(**ing.model_dump()))
    for step in v_in.procedure_steps:
        version.procedure_steps.append(RecipeProcedureStep(**step.model_dump()))
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.put("/versions/{version_id}", response_model=RecipeVersionResponse)
def update_recipe_version(
    version_id: int, v_in: RecipeVersionCreate,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    version = db.query(RecipeVersion).filter(RecipeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Recipe version not found")
    if version.status == "published":
        raise HTTPException(status_code=400, detail="Cannot edit a published version")
    version.comment = v_in.comment
    version.batch_size = v_in.batch_size
    version.batch_uom_id = v_in.batch_uom_id
    version.expected_yield_percent = v_in.expected_yield_percent
    # Replace ingredients
    for ing in version.ingredients:
        db.delete(ing)
    for ing in v_in.ingredients:
        version.ingredients.append(RecipeIngredient(**ing.model_dump()))
    # Replace procedure steps
    for step in version.procedure_steps:
        db.delete(step)
    for step in v_in.procedure_steps:
        version.procedure_steps.append(RecipeProcedureStep(**step.model_dump()))
    db.commit()
    db.refresh(version)
    return version


@router.post("/versions/{version_id}/publish", response_model=RecipeVersionResponse)
def publish_recipe_version(
    version_id: int,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    version = db.query(RecipeVersion).filter(RecipeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Recipe version not found")
    if version.status == "published":
        raise HTTPException(status_code=400, detail="Already published")
    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(version)
    return version


@router.post("/{recipe_id}/clone", response_model=RecipeVersionResponse)
def clone_recipe_version(
    recipe_id: int,
    source_version_id: Optional[int] = None,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    # Find source version
    if source_version_id:
        source = db.query(RecipeVersion).filter(
            RecipeVersion.id == source_version_id,
            RecipeVersion.recipe_id == recipe_id,
        ).first()
    else:
        source = db.query(RecipeVersion).filter(
            RecipeVersion.recipe_id == recipe_id,
        ).order_by(RecipeVersion.version_number.desc()).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source version not found")
    max_ver = db.query(sa_func.max(RecipeVersion.version_number)).filter(
        RecipeVersion.recipe_id == recipe_id
    ).scalar() or 0
    new_version = RecipeVersion(
        recipe_id=recipe_id,
        version_number=max_ver + 1,
        status="draft",
        comment=f"Cloned from version {source.version_number:02d}",
        batch_size=source.batch_size,
        batch_uom_id=source.batch_uom_id,
        expected_yield_percent=source.expected_yield_percent,
    )
    for ing in source.ingredients:
        new_version.ingredients.append(RecipeIngredient(
            item_id=ing.item_id,
            sequence=ing.sequence,
            weight_percent=ing.weight_percent,
            notes=ing.notes,
        ))
    for step in source.procedure_steps:
        new_version.procedure_steps.append(RecipeProcedureStep(
            sequence=step.sequence,
            step_type=step.step_type,
            instruction_text=step.instruction_text,
        ))
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


# ===== BATCH / REPACK TICKETS =====

def _generate_ticket_number(db: Session, ticket_type: str) -> str:
    prefix = "BT" if ticket_type == "batch" else "RT"
    last = db.query(BatchTicket).filter(
        BatchTicket.ticket_type == ticket_type
    ).order_by(BatchTicket.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"{prefix}-{num:06d}"


def _check_material_availability(db: Session, ticket: BatchTicket):
    """Check if enough material is on hand for the batch ticket."""
    has_any_shortage = False
    shortage_items = []
    for mat in ticket.planned_materials:
        available = db.query(sa_func.coalesce(sa_func.sum(Lot.quantity_on_hand), 0)).filter(
            Lot.item_id == mat.item_id,
            Lot.quantity_on_hand > 0,
            Lot.status == "available",
        ).scalar()
        mat.available_quantity = available
        if available < mat.planned_quantity:
            mat.has_shortage = True
            has_any_shortage = True
            item = db.query(Item).filter(Item.id == mat.item_id).first()
            shortage_items.append({
                "item_id": mat.item_id,
                "item_code": item.item_code if item else "?",
                "required": float(mat.planned_quantity),
                "available": float(available),
                "short": float(mat.planned_quantity - available),
            })
        else:
            mat.has_shortage = False
    ticket.has_shortage = has_any_shortage
    if shortage_items:
        import json
        ticket.shortage_details = json.dumps(shortage_items)
    else:
        ticket.shortage_details = None


@router.get("/batch-tickets", response_model=List[BatchTicketResponse])
def list_batch_tickets(
    ticket_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user=Depends(require_permission("manufacturing", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(BatchTicket)
    if ticket_type:
        q = q.filter(BatchTicket.ticket_type == ticket_type)
    if status_filter:
        q = q.filter(BatchTicket.status == status_filter)
    return q.order_by(BatchTicket.created_at.desc()).all()


@router.post("/batch-tickets", response_model=BatchTicketResponse, status_code=status.HTTP_201_CREATED)
def create_batch_ticket(
    bt_in: BatchTicketCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == bt_in.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    ticket = BatchTicket(
        ticket_number=_generate_ticket_number(db, bt_in.ticket_type),
        ticket_type=bt_in.ticket_type,
        recipe_id=bt_in.recipe_id,
        recipe_version_id=bt_in.recipe_version_id,
        item_id=bt_in.item_id,
        planned_quantity=bt_in.planned_quantity,
        due_date=bt_in.due_date,
        customer_id=bt_in.customer_id,
        shortage_override=bt_in.shortage_override,
        notes=bt_in.notes,
        status="draft",
        created_by=current_user.id,
    )
    for pkg in bt_in.packages:
        ticket.packages.append(BatchTicketPackage(
            pack_extension_id=pkg.pack_extension_id,
            quantity=pkg.quantity,
        ))
    # Calculate planned materials from recipe
    if bt_in.recipe_version_id:
        version = db.query(RecipeVersion).filter(RecipeVersion.id == bt_in.recipe_version_id).first()
        if version and version.ingredients:
            for ing in version.ingredients:
                planned_qty = bt_in.planned_quantity * ing.weight_percent / Decimal("100")
                ticket.planned_materials.append(BatchTicketMaterial(
                    item_id=ing.item_id,
                    planned_quantity=planned_qty,
                ))
    db.add(ticket)
    db.flush()
    # Check availability
    _check_material_availability(db, ticket)
    if ticket.has_shortage and not bt_in.shortage_override:
        ticket.status = "draft"
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/batch-tickets/{ticket_id}", response_model=BatchTicketResponse)
def get_batch_ticket(ticket_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(BatchTicket).filter(BatchTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Batch ticket not found")
    # Refresh shortage check
    _check_material_availability(db, ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/batch-tickets/{ticket_id}", response_model=BatchTicketResponse)
def update_batch_ticket(
    ticket_id: int, bt_in: BatchTicketUpdate,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    ticket = db.query(BatchTicket).filter(BatchTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Batch ticket not found")
    for k, v in bt_in.model_dump(exclude_unset=True).items():
        setattr(ticket, k, v)
    db.commit()
    db.refresh(ticket)
    return ticket


# ===== BATCH EXECUTION =====

@router.post("/batch-tickets/{ticket_id}/execute", response_model=BatchExecutionResponse)
def start_batch_execution(
    ticket_id: int, req: BatchExecutionStart,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    ticket = db.query(BatchTicket).filter(BatchTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Batch ticket not found")
    if ticket.execution:
        raise HTTPException(status_code=400, detail="Execution already started")
    if ticket.has_shortage and not ticket.shortage_override:
        raise HTTPException(status_code=400, detail="Material shortage exists. Override or resolve before execution.")
    execution = BatchExecution(
        batch_ticket_id=ticket_id,
        executed_by=current_user.id,
        notes=req.notes,
    )
    # Pre-populate planned consumptions
    for mat in ticket.planned_materials:
        execution.consumptions.append(BatchExecutionConsumption(
            item_id=mat.item_id,
            planned_quantity=mat.planned_quantity,
            actual_quantity=Decimal("0"),
        ))
    ticket.status = "in_progress"
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


@router.get("/batch-tickets/{ticket_id}/execution", response_model=BatchExecutionResponse)
def get_batch_execution(ticket_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    execution = db.query(BatchExecution).filter(BatchExecution.batch_ticket_id == ticket_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/batch-tickets/{ticket_id}/execute/consume")
def record_batch_consumption(
    ticket_id: int, req: BatchExecutionConsumeRequest,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    execution = db.query(BatchExecution).filter(BatchExecution.batch_ticket_id == ticket_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status == "completed":
        raise HTTPException(status_code=400, detail="Execution already completed")
    ticket = execution.batch_ticket
    for c in req.consumptions:
        lot = db.query(Lot).filter(Lot.id == c.lot_id).first()
        if not lot or lot.quantity_on_hand < c.actual_quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient inventory for lot {c.lot_id}")
        lot.quantity_on_hand -= c.actual_quantity
        # FIFO cost consumption
        remaining = c.actual_quantity
        total_cost = Decimal("0")
        layers = db.query(FIFOCostLayer).filter(
            FIFOCostLayer.item_id == c.item_id,
            FIFOCostLayer.lot_id == c.lot_id,
            FIFOCostLayer.quantity_remaining > 0,
        ).order_by(FIFOCostLayer.received_date).all()
        for layer in layers:
            if remaining <= 0:
                break
            consume = min(remaining, layer.quantity_remaining)
            layer.quantity_remaining -= consume
            total_cost += consume * layer.unit_cost
            remaining -= consume
        unit_cost = total_cost / c.actual_quantity if c.actual_quantity else 0
        # Update or create consumption record
        existing = None
        for ec in execution.consumptions:
            if ec.item_id == c.item_id and (ec.lot_id == c.lot_id or ec.lot_id is None):
                existing = ec
                break
        if existing:
            existing.lot_id = c.lot_id
            existing.actual_quantity = c.actual_quantity
            existing.unit_cost = unit_cost
            existing.total_cost = total_cost
        else:
            execution.consumptions.append(BatchExecutionConsumption(
                item_id=c.item_id, lot_id=c.lot_id,
                actual_quantity=c.actual_quantity,
                unit_cost=unit_cost, total_cost=total_cost,
            ))
        # Record inventory transaction
        item = db.query(Item).filter(Item.id == c.item_id).first()
        txn = InventoryTransaction(
            transaction_type="consumption",
            item_id=c.item_id, lot_id=c.lot_id,
            quantity=-c.actual_quantity,
            unit_cost=unit_cost, total_cost=total_cost,
            gl_group_id=item.gl_group_id if item else None,
            reference_type="batch_ticket", reference_id=ticket.id,
            created_by=current_user.id,
        )
        db.add(txn)
    db.commit()
    return {"detail": "Consumption recorded"}


@router.post("/batch-tickets/{ticket_id}/execute/complete")
def complete_batch_execution(
    ticket_id: int, req: BatchExecutionCompleteRequest,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    execution = db.query(BatchExecution).filter(BatchExecution.batch_ticket_id == ticket_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status == "completed":
        raise HTTPException(status_code=400, detail="Execution already completed")
    ticket = execution.batch_ticket
    # Calculate cost from consumptions
    total_input_cost = sum(float(c.total_cost or 0) for c in execution.consumptions if c.actual_quantity)
    unit_cost = Decimal(str(total_input_cost / float(req.output.quantity))) if req.output.quantity else 0
    # Create output lot
    lot = Lot(
        lot_number=req.output.lot_number,
        item_id=ticket.item_id,
        warehouse_id=req.output.warehouse_id,
        quantity_on_hand=req.output.quantity,
        status="available",
        received_date=datetime.now(timezone.utc),
    )
    db.add(lot)
    db.flush()
    # FIFO cost layer for output
    layer = FIFOCostLayer(
        item_id=ticket.item_id, lot_id=lot.id,
        quantity_remaining=req.output.quantity,
        unit_cost=unit_cost,
        total_cost=unit_cost * req.output.quantity,
        reference_type="batch_execution", reference_id=execution.id,
    )
    db.add(layer)
    execution.outputs.append(BatchExecutionOutput(
        item_id=ticket.item_id, lot_id=lot.id,
        quantity=req.output.quantity,
        unit_cost=unit_cost, total_cost=unit_cost * req.output.quantity,
    ))
    execution.actual_yield = req.output.quantity
    execution.yield_percent = (req.output.quantity / ticket.planned_quantity * 100) if ticket.planned_quantity else 0
    execution.status = "completed"
    execution.completed_at = datetime.now(timezone.utc)
    execution.notes = req.notes or execution.notes
    ticket.status = "completed"
    # Inventory transaction for output
    item = db.query(Item).filter(Item.id == ticket.item_id).first()
    txn = InventoryTransaction(
        transaction_type="output",
        item_id=ticket.item_id, lot_id=lot.id,
        warehouse_id=req.output.warehouse_id,
        quantity=req.output.quantity,
        unit_cost=unit_cost,
        total_cost=unit_cost * req.output.quantity,
        gl_group_id=item.gl_group_id if item else None,
        reference_type="batch_ticket", reference_id=ticket.id,
        created_by=current_user.id,
    )
    db.add(txn)
    db.commit()
    return {
        "detail": "Batch execution completed",
        "lot_number": lot.lot_number,
        "quantity": float(req.output.quantity),
        "unit_cost": float(unit_cost),
        "yield_percent": float(execution.yield_percent),
    }
