from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.inventory import Item, Lot, Warehouse, Location, InventoryTransaction, FIFOCostLayer, UnitOfMeasure
from app.schemas.inventory import (
    ItemCreate, ItemUpdate, ItemResponse,
    WarehouseCreate, WarehouseResponse,
    LocationCreate, LocationResponse,
    LotCreate, LotResponse,
    InventoryAdjustment, InventoryTransfer, InventoryTransactionResponse,
    UOMCreate, UOMResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# --- Items ---

@router.get("/items", response_model=List[ItemResponse])
def list_items(
    item_type: Optional[str] = None, is_active: bool = True,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Item).filter(Item.is_active == is_active)
    if item_type:
        q = q.filter(Item.item_type == item_type)
    return q.offset(skip).limit(limit).all()


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    item_in: ItemCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    if db.query(Item).filter(Item.item_code == item_in.item_code).first():
        raise HTTPException(status_code=400, detail="Item code already exists")
    item = Item(**item_in.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int, item_in: ItemUpdate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


# --- Warehouses ---

@router.get("/warehouses", response_model=List[WarehouseResponse])
def list_warehouses(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Warehouse).all()


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    wh_in: WarehouseCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    wh = Warehouse(**wh_in.model_dump())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


# --- Locations ---

@router.get("/locations", response_model=List[LocationResponse])
def list_locations(
    warehouse_id: Optional[int] = None,
    current_user=Depends(get_current_user), db: Session = Depends(get_db),
):
    q = db.query(Location)
    if warehouse_id:
        q = q.filter(Location.warehouse_id == warehouse_id)
    return q.all()


@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    loc_in: LocationCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    loc = Location(**loc_in.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


# --- Lots ---

@router.get("/lots", response_model=List[LotResponse])
def list_lots(
    item_id: Optional[int] = None, status_filter: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Lot)
    if item_id:
        q = q.filter(Lot.item_id == item_id)
    if status_filter:
        q = q.filter(Lot.status == status_filter)
    return q.offset(skip).limit(limit).all()


@router.get("/lots/{lot_id}", response_model=LotResponse)
def get_lot(lot_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    return lot


# --- Transactions ---

@router.get("/transactions", response_model=List[InventoryTransactionResponse])
def list_transactions(
    item_id: Optional[int] = None, lot_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(InventoryTransaction)
    if item_id:
        q = q.filter(InventoryTransaction.item_id == item_id)
    if lot_id:
        q = q.filter(InventoryTransaction.lot_id == lot_id)
    if transaction_type:
        q = q.filter(InventoryTransaction.transaction_type == transaction_type)
    return q.order_by(InventoryTransaction.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/adjustments", response_model=InventoryTransactionResponse)
def create_adjustment(
    adj: InventoryAdjustment,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == adj.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    lot = None
    if adj.lot_id:
        lot = db.query(Lot).filter(Lot.id == adj.lot_id).first()
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        lot.quantity_on_hand += adj.quantity
    txn = InventoryTransaction(
        transaction_type="adjustment",
        item_id=adj.item_id,
        lot_id=adj.lot_id,
        warehouse_id=adj.warehouse_id,
        location_id=adj.location_id,
        quantity=adj.quantity,
        unit_cost=adj.unit_cost,
        total_cost=(adj.unit_cost * adj.quantity) if adj.unit_cost else None,
        gl_group_id=item.gl_group_id,
        notes=adj.reason,
        created_by=current_user.id,
    )
    db.add(txn)
    if adj.quantity > 0 and adj.unit_cost:
        layer = FIFOCostLayer(
            item_id=adj.item_id, lot_id=adj.lot_id,
            quantity_remaining=adj.quantity, unit_cost=adj.unit_cost,
            total_cost=adj.unit_cost * adj.quantity,
            reference_type="adjustment", reference_id=None,
        )
        db.add(layer)
    db.commit()
    db.refresh(txn)
    return txn


@router.post("/transfers")
def create_transfer(
    xfer: InventoryTransfer,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    lot = db.query(Lot).filter(Lot.id == xfer.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    if lot.quantity_on_hand < xfer.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    lot.warehouse_id = xfer.to_warehouse_id
    lot.location_id = xfer.to_location_id
    txn = InventoryTransaction(
        transaction_type="transfer",
        item_id=xfer.item_id, lot_id=xfer.lot_id,
        warehouse_id=xfer.to_warehouse_id, location_id=xfer.to_location_id,
        quantity=xfer.quantity, created_by=current_user.id,
    )
    db.add(txn)
    db.commit()
    return {"detail": "Transfer completed"}


# --- UOMs ---

@router.get("/uoms", response_model=List[UOMResponse])
def list_uoms(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UnitOfMeasure).all()


@router.post("/uoms", response_model=UOMResponse, status_code=status.HTTP_201_CREATED)
def create_uom(
    uom_in: UOMCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    uom = UnitOfMeasure(**uom_in.model_dump())
    db.add(uom)
    db.commit()
    db.refresh(uom)
    return uom


# --- FIFO Valuation ---

@router.get("/valuation")
def get_fifo_valuation(
    item_id: Optional[int] = None,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(FIFOCostLayer).filter(FIFOCostLayer.quantity_remaining > 0)
    if item_id:
        q = q.filter(FIFOCostLayer.item_id == item_id)
    layers = q.order_by(FIFOCostLayer.received_date).all()
    result = []
    for l in layers:
        result.append({
            "id": l.id, "item_id": l.item_id, "lot_id": l.lot_id,
            "quantity_remaining": float(l.quantity_remaining),
            "unit_cost": float(l.unit_cost),
            "total_value": float(l.quantity_remaining * l.unit_cost),
            "received_date": l.received_date.isoformat() if l.received_date else None,
        })
    return result
