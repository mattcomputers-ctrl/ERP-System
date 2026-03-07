from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.manufacturing import (
    Formula, FormulaVersion, FormulaIngredient,
    ProductionOrder, ProductionConsumption, ProductionOutput,
)
from app.models.inventory import Item, Lot, InventoryTransaction, FIFOCostLayer
from app.schemas.manufacturing import (
    FormulaCreate, FormulaResponse,
    FormulaVersionCreate, FormulaVersionResponse, FormulaVersionRevert,
    ProductionOrderCreate, ProductionOrderUpdate, ProductionOrderResponse,
    ProductionConsumptionCreate, ProductionOutputCreate,
)

router = APIRouter(prefix="/manufacturing", tags=["Manufacturing"])


# --- Formulas ---

@router.get("/formulas", response_model=List[FormulaResponse])
def list_formulas(
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("manufacturing", "read")),
    db: Session = Depends(get_db),
):
    return db.query(Formula).filter(Formula.is_active == True).offset(skip).limit(limit).all()


@router.post("/formulas", response_model=FormulaResponse, status_code=status.HTTP_201_CREATED)
def create_formula(
    f_in: FormulaCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    if db.query(Formula).filter(Formula.code == f_in.code).first():
        raise HTTPException(status_code=400, detail="Formula code already exists")
    formula = Formula(
        code=f_in.code, name=f_in.name,
        product_item_id=f_in.product_item_id,
        description=f_in.description,
    )
    version = FormulaVersion(
        version_number=1,
        batch_size=f_in.initial_version.batch_size,
        batch_uom_id=f_in.initial_version.batch_uom_id,
        expected_yield_percent=f_in.initial_version.expected_yield_percent,
        notes=f_in.initial_version.notes,
        is_current=True,
    )
    for ing in f_in.initial_version.ingredients:
        ingredient = FormulaIngredient(**ing.model_dump())
        version.ingredients.append(ingredient)
    formula.versions.append(version)
    db.add(formula)
    db.commit()
    db.refresh(formula)
    return formula


@router.get("/formulas/{formula_id}", response_model=FormulaResponse)
def get_formula(formula_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.query(Formula).filter(Formula.id == formula_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Formula not found")
    return f


@router.post("/formulas/{formula_id}/versions", response_model=FormulaVersionResponse)
def add_formula_version(
    formula_id: int, v_in: FormulaVersionCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    formula = db.query(Formula).filter(Formula.id == formula_id).first()
    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")
    # Deactivate current versions
    for v in formula.versions:
        v.is_current = False
    max_ver = max((v.version_number for v in formula.versions), default=0)
    version = FormulaVersion(
        formula_id=formula_id,
        version_number=max_ver + 1,
        batch_size=v_in.batch_size,
        batch_uom_id=v_in.batch_uom_id,
        expected_yield_percent=v_in.expected_yield_percent,
        notes=v_in.notes,
        is_current=True,
    )
    for ing in v_in.ingredients:
        ingredient = FormulaIngredient(**ing.model_dump())
        version.ingredients.append(ingredient)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/formulas/{formula_id}/versions", response_model=List[FormulaVersionResponse])
def list_formula_versions(
    formula_id: int,
    current_user=Depends(require_permission("manufacturing", "read")),
    db: Session = Depends(get_db),
):
    formula = db.query(Formula).filter(Formula.id == formula_id).first()
    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")
    return db.query(FormulaVersion).filter(
        FormulaVersion.formula_id == formula_id
    ).order_by(FormulaVersion.version_number.desc()).all()


@router.post("/formulas/{formula_id}/versions/{version_id}/revert", response_model=FormulaVersionResponse)
def revert_formula_version(
    formula_id: int, version_id: int, revert_in: FormulaVersionRevert,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    formula = db.query(Formula).filter(Formula.id == formula_id).first()
    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")
    target_version = db.query(FormulaVersion).filter(
        FormulaVersion.id == version_id,
        FormulaVersion.formula_id == formula_id,
    ).first()
    if not target_version:
        raise HTTPException(status_code=404, detail="Formula version not found")
    # Deactivate all current versions
    for v in formula.versions:
        v.is_current = False
    max_ver = max((v.version_number for v in formula.versions), default=0)
    # Create new version copying from target
    new_version = FormulaVersion(
        formula_id=formula_id,
        version_number=max_ver + 1,
        batch_size=target_version.batch_size,
        batch_uom_id=target_version.batch_uom_id,
        expected_yield_percent=target_version.expected_yield_percent,
        notes=target_version.notes,
        change_reason=revert_in.reason,
        reverted_from_version_id=target_version.id,
        is_current=True,
    )
    # Copy ingredients from target version
    for ing in target_version.ingredients:
        new_ing = FormulaIngredient(
            item_id=ing.item_id,
            sequence=ing.sequence,
            quantity=ing.quantity,
            uom_id=ing.uom_id,
            percentage=ing.percentage,
            is_active=ing.is_active,
            notes=ing.notes,
        )
        new_version.ingredients.append(new_ing)
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


# --- Production Orders ---

def _generate_prod_number(db: Session) -> str:
    last = db.query(ProductionOrder).order_by(ProductionOrder.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"PRD-{num:06d}"


@router.get("/production-orders", response_model=List[ProductionOrderResponse])
def list_production_orders(
    status_filter: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("manufacturing", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(ProductionOrder)
    if status_filter:
        q = q.filter(ProductionOrder.status == status_filter)
    return q.order_by(ProductionOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/production-orders", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
def create_production_order(
    po_in: ProductionOrderCreate,
    current_user=Depends(require_permission("manufacturing", "create")),
    db: Session = Depends(get_db),
):
    formula = db.query(Formula).filter(Formula.id == po_in.formula_id).first()
    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")
    version = db.query(FormulaVersion).filter(FormulaVersion.id == po_in.formula_version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Formula version not found")
    prod_order = ProductionOrder(
        order_number=_generate_prod_number(db),
        formula_id=po_in.formula_id,
        formula_version_id=po_in.formula_version_id,
        planned_quantity=po_in.planned_quantity,
        planned_start_date=po_in.planned_start_date,
        planned_end_date=po_in.planned_end_date,
        output_warehouse_id=po_in.output_warehouse_id,
        output_location_id=po_in.output_location_id,
        notes=po_in.notes,
        created_by=current_user.id,
    )
    # Auto-generate planned consumptions based on formula scaling
    scale_factor = po_in.planned_quantity / version.batch_size if version.batch_size else 1
    for ing in version.ingredients:
        consumption = ProductionConsumption(
            item_id=ing.item_id,
            planned_quantity=ing.quantity * scale_factor,
        )
        prod_order.consumptions.append(consumption)
    db.add(prod_order)
    db.commit()
    db.refresh(prod_order)
    return prod_order


@router.get("/production-orders/{po_id}", response_model=ProductionOrderResponse)
def get_production_order(po_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")
    return po


@router.put("/production-orders/{po_id}", response_model=ProductionOrderResponse)
def update_production_order(
    po_id: int, po_in: ProductionOrderUpdate,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")
    for k, v in po_in.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    db.commit()
    db.refresh(po)
    return po


@router.post("/production-orders/{po_id}/consume")
def record_consumption(
    po_id: int, consumptions: List[ProductionConsumptionCreate],
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")
    if po.status not in ("released", "in_production"):
        raise HTTPException(status_code=400, detail="Production order must be released or in production")
    po.status = "in_production"
    po.actual_start_date = po.actual_start_date or datetime.now(timezone.utc)
    for c in consumptions:
        lot = db.query(Lot).filter(Lot.id == c.lot_id).first()
        if not lot or lot.quantity_on_hand < c.actual_quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient inventory for lot {c.lot_id}")
        lot.quantity_on_hand -= c.actual_quantity
        # Consume FIFO layers
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
        pc = db.query(ProductionConsumption).filter(
            ProductionConsumption.production_order_id == po_id,
            ProductionConsumption.item_id == c.item_id,
        ).first()
        if pc:
            pc.lot_id = c.lot_id
            pc.actual_quantity = c.actual_quantity
            pc.unit_cost = unit_cost
            pc.total_cost = total_cost
            pc.consumed_at = datetime.now(timezone.utc)
        else:
            pc = ProductionConsumption(
                production_order_id=po_id,
                item_id=c.item_id, lot_id=c.lot_id,
                planned_quantity=c.actual_quantity,
                actual_quantity=c.actual_quantity,
                unit_cost=unit_cost, total_cost=total_cost,
                consumed_at=datetime.now(timezone.utc),
            )
            db.add(pc)
        item = db.query(Item).filter(Item.id == c.item_id).first()
        txn = InventoryTransaction(
            transaction_type="consumption",
            item_id=c.item_id, lot_id=c.lot_id,
            quantity=-c.actual_quantity,
            unit_cost=unit_cost, total_cost=total_cost,
            gl_group_id=item.gl_group_id if item else None,
            reference_type="production_order", reference_id=po_id,
            created_by=current_user.id,
        )
        db.add(txn)
    db.commit()
    return {"detail": "Consumption recorded"}


@router.post("/production-orders/{po_id}/output")
def record_output(
    po_id: int, output: ProductionOutputCreate,
    current_user=Depends(require_permission("manufacturing", "update")),
    db: Session = Depends(get_db),
):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")
    formula = db.query(Formula).filter(Formula.id == po.formula_id).first()
    # Calculate cost from consumptions
    total_input_cost = sum(
        float(c.total_cost or 0) for c in po.consumptions if c.actual_quantity
    )
    unit_cost = Decimal(str(total_input_cost / float(output.quantity))) if output.quantity else 0
    # Create output lot
    lot = Lot(
        lot_number=output.lot_number,
        item_id=formula.product_item_id,
        warehouse_id=output.warehouse_id or po.output_warehouse_id,
        location_id=output.location_id or po.output_location_id,
        quantity_on_hand=output.quantity,
        status="available",
        received_date=datetime.now(timezone.utc),
    )
    db.add(lot)
    db.flush()
    po.output_lot_id = lot.id
    po.actual_quantity = output.quantity
    po.actual_end_date = datetime.now(timezone.utc)
    po.yield_percent = (output.quantity / po.planned_quantity * 100) if po.planned_quantity else 0
    po.status = "completed"
    # Create FIFO cost layer for output
    layer = FIFOCostLayer(
        item_id=formula.product_item_id, lot_id=lot.id,
        quantity_remaining=output.quantity,
        unit_cost=unit_cost,
        total_cost=unit_cost * output.quantity,
        reference_type="production_output", reference_id=po.id,
    )
    db.add(layer)
    prod_output = ProductionOutput(
        production_order_id=po.id,
        item_id=formula.product_item_id,
        lot_id=lot.id,
        quantity=output.quantity,
        unit_cost=unit_cost,
        total_cost=unit_cost * output.quantity,
    )
    db.add(prod_output)
    item = db.query(Item).filter(Item.id == formula.product_item_id).first()
    txn = InventoryTransaction(
        transaction_type="output",
        item_id=formula.product_item_id, lot_id=lot.id,
        warehouse_id=output.warehouse_id or po.output_warehouse_id,
        quantity=output.quantity,
        unit_cost=unit_cost,
        total_cost=unit_cost * output.quantity,
        gl_group_id=item.gl_group_id if item else None,
        reference_type="production_order", reference_id=po.id,
        created_by=current_user.id,
    )
    db.add(txn)
    db.commit()
    return {
        "detail": "Production output recorded",
        "lot_number": lot.lot_number,
        "quantity": float(output.quantity),
        "unit_cost": float(unit_cost),
        "yield_percent": float(po.yield_percent),
    }
