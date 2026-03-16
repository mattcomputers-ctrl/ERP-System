from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.inventory import (
    Item, ItemAlias, PackComponent, Lot, Warehouse, Location,
    InventoryTransaction, FIFOCostLayer, UnitOfMeasure,
    ItemActiveRecipe, QCTestDefinition, ItemQCTest,
    PackExtensionDefinition, PackExtensionMaterial, ItemPackExtension,
)
from app.schemas.inventory import (
    ItemCreate, ItemUpdate, ItemResponse,
    WarehouseCreate, WarehouseResponse,
    LocationCreate, LocationResponse,
    LotCreate, LotResponse,
    InventoryAdjustment, InventoryTransfer, InventoryTransactionResponse,
    UOMCreate, UOMUpdate, UOMResponse,
    ItemAliasCreate, ItemAliasUpdate, ItemAliasResponse,
    PackComponentCreate, PackComponentResponse, PackDefinitionCreate, PackOperationRequest,
    ItemActiveRecipeCreate, ItemActiveRecipeResponse,
    QCTestDefinitionCreate, QCTestDefinitionUpdate, QCTestDefinitionResponse,
    ItemQCTestCreate, ItemQCTestResponse,
    PackExtensionDefinitionCreate, PackExtensionDefinitionUpdate, PackExtensionDefinitionResponse,
    ItemPackExtensionCreate, ItemPackExtensionUpdate, ItemPackExtensionResponse,
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
    else:
        # Auto-create a lot for the adjustment
        from datetime import datetime, timezone
        pe = db.query(PackExtensionDefinition).filter(PackExtensionDefinition.id == adj.pack_extension_id).first() if adj.pack_extension_id else None
        suffix = pe.code if pe else ""
        lot_number = f"ADJ-{item.item_code}{suffix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        lot = Lot(
            lot_number=lot_number, item_id=adj.item_id,
            pack_extension_id=adj.pack_extension_id,
            warehouse_id=adj.warehouse_id, location_id=adj.location_id,
            quantity_on_hand=adj.quantity, status="available",
            received_date=datetime.now(timezone.utc),
        )
        db.add(lot)
        db.flush()
    txn = InventoryTransaction(
        transaction_type="adjustment",
        item_id=adj.item_id,
        lot_id=lot.id if lot else None,
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
            item_id=adj.item_id, lot_id=lot.id if lot else None,
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


@router.put("/uoms/{uom_id}", response_model=UOMResponse)
def update_uom(
    uom_id: int, uom_in: UOMUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    uom = db.query(UnitOfMeasure).filter(UnitOfMeasure.id == uom_id).first()
    if not uom:
        raise HTTPException(status_code=404, detail="UOM not found")
    for k, v in uom_in.model_dump(exclude_unset=True).items():
        setattr(uom, k, v)
    db.commit()
    db.refresh(uom)
    return uom


@router.delete("/uoms/{uom_id}")
def delete_uom(
    uom_id: int,
    current_user=Depends(require_permission("settings", "delete")),
    db: Session = Depends(get_db),
):
    uom = db.query(UnitOfMeasure).filter(UnitOfMeasure.id == uom_id).first()
    if not uom:
        raise HTTPException(status_code=404, detail="UOM not found")
    # Check if UOM is in use by any items
    in_use = db.query(Item).filter(Item.primary_uom_id == uom_id).first()
    if in_use:
        raise HTTPException(status_code=400, detail="Cannot delete UOM that is assigned to items. Update those items first.")
    db.delete(uom)
    db.commit()
    return {"detail": "UOM deleted"}


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


# --- Inventory Summary (on-hand by warehouse/item/pack extension) ---

@router.get("/summary")
def get_inventory_summary(
    warehouse_id: Optional[int] = None,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    """Aggregate on-hand inventory by warehouse, item, and pack extension.
    Only rows with qty > 0 are returned."""
    q = db.query(
        Lot.warehouse_id,
        Lot.item_id,
        Lot.pack_extension_id,
        sa_func.sum(Lot.quantity_on_hand).label("qty_on_hand"),
        sa_func.sum(Lot.quantity_allocated).label("qty_allocated"),
    ).filter(
        Lot.quantity_on_hand > 0
    ).group_by(
        Lot.warehouse_id, Lot.item_id, Lot.pack_extension_id,
    )
    if warehouse_id:
        q = q.filter(Lot.warehouse_id == warehouse_id)

    rows = q.all()
    result = []
    for row in rows:
        item = db.query(Item).filter(Item.id == row.item_id).first()
        wh = db.query(Warehouse).filter(Warehouse.id == row.warehouse_id).first() if row.warehouse_id else None
        pe = db.query(PackExtensionDefinition).filter(PackExtensionDefinition.id == row.pack_extension_id).first() if row.pack_extension_id else None
        uom = db.query(UnitOfMeasure).filter(UnitOfMeasure.id == item.primary_uom_id).first() if item and item.primary_uom_id else None
        from app.models.gl_group import GLGroup
        gl = db.query(GLGroup).filter(GLGroup.id == item.gl_group_id).first() if item and item.gl_group_id else None

        item_code = item.item_code if item else ""
        if pe:
            item_code = f"{item_code}{pe.code}"

        result.append({
            "warehouse_code": wh.code if wh else "Unassigned",
            "warehouse_name": wh.name if wh else "Unassigned",
            "warehouse_id": row.warehouse_id,
            "item_id": row.item_id,
            "item_code": item_code,
            "item_base_code": item.item_code if item else "",
            "item_name": item.name if item else "",
            "pack_extension_id": row.pack_extension_id,
            "pack_extension_code": pe.code if pe else None,
            "pack_extension_name": pe.name if pe else None,
            "qty_on_hand": float(row.qty_on_hand),
            "qty_allocated": float(row.qty_allocated),
            "uom_abbreviation": uom.abbreviation if uom else "",
            "gl_group_name": gl.name if gl else "",
        })
    result.sort(key=lambda r: (r["warehouse_code"], r["item_code"]))
    return result


# --- Item Aliases ---

@router.get("/items/{item_id}/aliases", response_model=List[ItemAliasResponse])
def list_item_aliases(
    item_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.query(ItemAlias).filter(ItemAlias.item_id == item_id).all()


@router.post("/items/{item_id}/aliases", response_model=ItemAliasResponse, status_code=status.HTTP_201_CREATED)
def create_item_alias(
    item_id: int, alias_in: ItemAliasCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    existing = db.query(ItemAlias).filter(
        ItemAlias.alias_code == alias_in.alias_code,
        ItemAlias.alias_type == alias_in.alias_type,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Alias code already exists for this type")
    alias = ItemAlias(item_id=item_id, **alias_in.model_dump())
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


@router.put("/aliases/{alias_id}", response_model=ItemAliasResponse)
def update_item_alias(
    alias_id: int, alias_in: ItemAliasUpdate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    alias = db.query(ItemAlias).filter(ItemAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")
    for key, value in alias_in.model_dump(exclude_unset=True).items():
        setattr(alias, key, value)
    db.commit()
    db.refresh(alias)
    return alias


@router.delete("/aliases/{alias_id}")
def delete_item_alias(
    alias_id: int,
    current_user=Depends(require_permission("inventory", "delete")),
    db: Session = Depends(get_db),
):
    alias = db.query(ItemAlias).filter(ItemAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")
    db.delete(alias)
    db.commit()
    return {"detail": "Alias deleted"}


@router.get("/aliases/lookup")
def lookup_by_alias(
    alias_code: str,
    alias_type: Optional[str] = None,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    """Look up an item by its alias code. Returns the item and matching alias."""
    q = db.query(ItemAlias).filter(ItemAlias.alias_code == alias_code, ItemAlias.is_active == True)
    if alias_type:
        q = q.filter(ItemAlias.alias_type == alias_type)
    aliases = q.all()
    if not aliases:
        raise HTTPException(status_code=404, detail="No item found for this alias")
    results = []
    for a in aliases:
        item = db.query(Item).filter(Item.id == a.item_id).first()
        results.append({
            "alias_id": a.id,
            "alias_code": a.alias_code,
            "alias_name": a.alias_name,
            "alias_type": a.alias_type,
            "item_id": item.id if item else None,
            "item_code": item.item_code if item else None,
            "item_name": item.name if item else None,
        })
    return results


# --- Pack Components ---

@router.get("/items/{item_id}/pack-components", response_model=List[PackComponentResponse])
def list_pack_components(
    item_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.query(PackComponent).filter(
        PackComponent.pack_item_id == item_id, PackComponent.is_active == True
    ).order_by(PackComponent.sequence).all()


@router.put("/items/{item_id}/pack-components")
def set_pack_components(
    item_id: int, pack_def: PackDefinitionCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    """Set or replace the full pack definition for an item."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    # Validate no self-reference
    for comp in pack_def.components:
        if comp.component_item_id == item_id:
            raise HTTPException(status_code=400, detail="A pack cannot contain itself")
        comp_item = db.query(Item).filter(Item.id == comp.component_item_id).first()
        if not comp_item:
            raise HTTPException(status_code=404, detail=f"Component item {comp.component_item_id} not found")
    # Remove existing components
    db.query(PackComponent).filter(PackComponent.pack_item_id == item_id).delete()
    # Add new components
    created = []
    for comp in pack_def.components:
        pc = PackComponent(pack_item_id=item_id, **comp.model_dump())
        db.add(pc)
        created.append(pc)
    db.commit()
    for c in created:
        db.refresh(c)
    return {"detail": f"{len(created)} pack components set", "count": len(created)}


@router.post("/items/{item_id}/pack-components", response_model=PackComponentResponse, status_code=status.HTTP_201_CREATED)
def add_pack_component(
    item_id: int, comp_in: PackComponentCreate,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    """Add a single component to a pack definition."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if comp_in.component_item_id == item_id:
        raise HTTPException(status_code=400, detail="A pack cannot contain itself")
    existing = db.query(PackComponent).filter(
        PackComponent.pack_item_id == item_id,
        PackComponent.component_item_id == comp_in.component_item_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Component already exists in this pack")
    pc = PackComponent(pack_item_id=item_id, **comp_in.model_dump())
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc


@router.delete("/pack-components/{component_id}")
def delete_pack_component(
    component_id: int,
    current_user=Depends(require_permission("inventory", "delete")),
    db: Session = Depends(get_db),
):
    pc = db.query(PackComponent).filter(PackComponent.id == component_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Pack component not found")
    db.delete(pc)
    db.commit()
    return {"detail": "Pack component removed"}


@router.post("/packs/assemble")
def assemble_pack(
    op: PackOperationRequest,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    """Assemble packs: consume component lots and create pack lot."""
    pack_item = db.query(Item).filter(Item.id == op.pack_item_id).first()
    if not pack_item:
        raise HTTPException(status_code=404, detail="Pack item not found")
    components = db.query(PackComponent).filter(
        PackComponent.pack_item_id == op.pack_item_id, PackComponent.is_active == True
    ).all()
    if not components:
        raise HTTPException(status_code=400, detail="No pack components defined for this item")
    # Build lot mapping from request
    lot_map = {}
    if op.component_lots:
        for cl in op.component_lots:
            lot_map[cl["component_item_id"]] = cl["lot_id"]
    # Consume component inventory
    total_cost = Decimal("0")
    for comp in components:
        required_qty = comp.quantity * op.quantity
        lot_id = lot_map.get(comp.component_item_id)
        if not lot_id:
            raise HTTPException(status_code=400, detail=f"No lot specified for component item {comp.component_item_id}")
        lot = db.query(Lot).filter(Lot.id == lot_id).first()
        if not lot or lot.quantity_on_hand < required_qty:
            raise HTTPException(status_code=400, detail=f"Insufficient quantity for lot {lot_id}")
        lot.quantity_on_hand -= required_qty
        # Consume FIFO
        remaining = required_qty
        layers = db.query(FIFOCostLayer).filter(
            FIFOCostLayer.item_id == comp.component_item_id,
            FIFOCostLayer.lot_id == lot_id,
            FIFOCostLayer.quantity_remaining > 0,
        ).order_by(FIFOCostLayer.received_date).all()
        for layer in layers:
            if remaining <= 0:
                break
            consume = min(remaining, layer.quantity_remaining)
            layer.quantity_remaining -= consume
            total_cost += consume * layer.unit_cost
            remaining -= consume
        txn = InventoryTransaction(
            transaction_type="pack_consumption",
            item_id=comp.component_item_id, lot_id=lot_id,
            warehouse_id=op.warehouse_id,
            quantity=-required_qty,
            gl_group_id=pack_item.gl_group_id,
            reference_type="pack_assembly", reference_id=op.pack_item_id,
            created_by=current_user.id,
        )
        db.add(txn)
    # Create pack output lot
    from datetime import datetime, timezone
    lot_number = op.lot_number or f"PCK-{pack_item.item_code}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    pack_lot = Lot(
        lot_number=lot_number, item_id=op.pack_item_id,
        warehouse_id=op.warehouse_id, location_id=op.location_id,
        quantity_on_hand=op.quantity, status="available",
        received_date=datetime.now(timezone.utc),
    )
    db.add(pack_lot)
    db.flush()
    unit_cost = total_cost / op.quantity if op.quantity else 0
    layer = FIFOCostLayer(
        item_id=op.pack_item_id, lot_id=pack_lot.id,
        quantity_remaining=op.quantity, unit_cost=unit_cost,
        total_cost=total_cost, reference_type="pack_assembly",
    )
    db.add(layer)
    txn = InventoryTransaction(
        transaction_type="pack_output",
        item_id=op.pack_item_id, lot_id=pack_lot.id,
        warehouse_id=op.warehouse_id, location_id=op.location_id,
        quantity=op.quantity, unit_cost=unit_cost, total_cost=total_cost,
        gl_group_id=pack_item.gl_group_id,
        reference_type="pack_assembly",
        created_by=current_user.id,
    )
    db.add(txn)
    db.commit()
    return {
        "detail": "Pack assembled",
        "lot_number": lot_number,
        "quantity": float(op.quantity),
        "unit_cost": float(unit_cost),
    }


@router.post("/packs/disassemble")
def disassemble_pack(
    op: PackOperationRequest,
    current_user=Depends(require_permission("inventory", "create")),
    db: Session = Depends(get_db),
):
    """Disassemble packs: consume pack lot and create component lots."""
    pack_item = db.query(Item).filter(Item.id == op.pack_item_id).first()
    if not pack_item:
        raise HTTPException(status_code=404, detail="Pack item not found")
    components = db.query(PackComponent).filter(
        PackComponent.pack_item_id == op.pack_item_id, PackComponent.is_active == True
    ).all()
    if not components:
        raise HTTPException(status_code=400, detail="No pack components defined for this item")
    # Find and consume pack lot
    lot_map = {}
    if op.component_lots:
        for cl in op.component_lots:
            lot_map[cl.get("component_item_id")] = cl.get("lot_id")
    pack_lot_id = lot_map.get(op.pack_item_id)
    if not pack_lot_id:
        raise HTTPException(status_code=400, detail="No pack lot specified (provide pack_item_id in component_lots)")
    pack_lot = db.query(Lot).filter(Lot.id == pack_lot_id).first()
    if not pack_lot or pack_lot.quantity_on_hand < op.quantity:
        raise HTTPException(status_code=400, detail="Insufficient pack quantity")
    pack_lot.quantity_on_hand -= op.quantity
    # Get pack unit cost
    pack_layers = db.query(FIFOCostLayer).filter(
        FIFOCostLayer.item_id == op.pack_item_id,
        FIFOCostLayer.lot_id == pack_lot_id,
        FIFOCostLayer.quantity_remaining > 0,
    ).order_by(FIFOCostLayer.received_date).all()
    remaining = op.quantity
    total_cost = Decimal("0")
    for layer in pack_layers:
        if remaining <= 0:
            break
        consume = min(remaining, layer.quantity_remaining)
        layer.quantity_remaining -= consume
        total_cost += consume * layer.unit_cost
        remaining -= consume
    from datetime import datetime, timezone
    txn = InventoryTransaction(
        transaction_type="pack_disassemble",
        item_id=op.pack_item_id, lot_id=pack_lot_id,
        quantity=-op.quantity, unit_cost=total_cost / op.quantity if op.quantity else 0,
        total_cost=total_cost,
        gl_group_id=pack_item.gl_group_id,
        reference_type="pack_disassembly",
        created_by=current_user.id,
    )
    db.add(txn)
    # Create component lots
    created_lots = []
    total_components = sum(c.quantity for c in components)
    for comp in components:
        output_qty = comp.quantity * op.quantity
        comp_cost = total_cost * (comp.quantity / total_components) if total_components else 0
        comp_unit_cost = comp_cost / output_qty if output_qty else 0
        comp_item = db.query(Item).filter(Item.id == comp.component_item_id).first()
        lot_num = f"UNPACK-{comp_item.item_code if comp_item else comp.component_item_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        comp_lot = Lot(
            lot_number=lot_num, item_id=comp.component_item_id,
            warehouse_id=op.warehouse_id, location_id=op.location_id,
            quantity_on_hand=output_qty, status="available",
            received_date=datetime.now(timezone.utc),
        )
        db.add(comp_lot)
        db.flush()
        layer = FIFOCostLayer(
            item_id=comp.component_item_id, lot_id=comp_lot.id,
            quantity_remaining=output_qty, unit_cost=comp_unit_cost,
            total_cost=comp_cost, reference_type="pack_disassembly",
        )
        db.add(layer)
        txn = InventoryTransaction(
            transaction_type="pack_disassemble_output",
            item_id=comp.component_item_id, lot_id=comp_lot.id,
            warehouse_id=op.warehouse_id, quantity=output_qty,
            unit_cost=comp_unit_cost, total_cost=comp_cost,
            reference_type="pack_disassembly",
            created_by=current_user.id,
        )
        db.add(txn)
        created_lots.append({"item_id": comp.component_item_id, "lot_number": lot_num, "quantity": float(output_qty)})
    db.commit()
    return {"detail": "Pack disassembled", "component_lots": created_lots}


# --- Item Active Recipes ---

@router.get("/items/{item_id}/active-recipes", response_model=List[ItemActiveRecipeResponse])
def list_active_recipes(
    item_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.query(ItemActiveRecipe).filter(ItemActiveRecipe.item_id == item_id).all()


@router.put("/items/{item_id}/active-recipes")
def set_active_recipes(
    item_id: int, recipes: List[ItemActiveRecipeCreate],
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    """Set the active recipes for an item. Exactly one must be master."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if recipes:
        master_count = sum(1 for r in recipes if r.is_master)
        if master_count != 1:
            raise HTTPException(status_code=400, detail="Exactly one recipe must be designated as master")
    # Remove existing
    db.query(ItemActiveRecipe).filter(ItemActiveRecipe.item_id == item_id).delete()
    created = []
    for r in recipes:
        ar = ItemActiveRecipe(item_id=item_id, formula_id=r.formula_id, is_master=r.is_master)
        db.add(ar)
        created.append(ar)
        if r.is_master:
            item.master_recipe_id = r.formula_id
    if not recipes:
        item.master_recipe_id = None
    db.commit()
    return {"detail": f"{len(created)} active recipes set"}


# --- Item QC Test Assignments ---

@router.get("/items/{item_id}/qc-tests", response_model=List[ItemQCTestResponse])
def list_item_qc_tests(
    item_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.query(ItemQCTest).filter(ItemQCTest.item_id == item_id).all()


@router.post("/items/{item_id}/qc-tests", response_model=ItemQCTestResponse, status_code=status.HTTP_201_CREATED)
def add_item_qc_test(
    item_id: int, test_in: ItemQCTestCreate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    existing = db.query(ItemQCTest).filter(
        ItemQCTest.item_id == item_id,
        ItemQCTest.qc_test_definition_id == test_in.qc_test_definition_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="QC test already assigned to this item")
    assignment = ItemQCTest(item_id=item_id, **test_in.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.put("/items/{item_id}/qc-tests/{assignment_id}", response_model=ItemQCTestResponse)
def update_item_qc_test(
    item_id: int, assignment_id: int, test_in: ItemQCTestCreate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    assignment = db.query(ItemQCTest).filter(
        ItemQCTest.id == assignment_id, ItemQCTest.item_id == item_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="QC test assignment not found")
    for key, value in test_in.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/items/{item_id}/qc-tests/{assignment_id}")
def remove_item_qc_test(
    item_id: int, assignment_id: int,
    current_user=Depends(require_permission("inventory", "delete")),
    db: Session = Depends(get_db),
):
    assignment = db.query(ItemQCTest).filter(
        ItemQCTest.id == assignment_id, ItemQCTest.item_id == item_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="QC test assignment not found")
    db.delete(assignment)
    db.commit()
    return {"detail": "QC test removed from item"}


# --- QC Test Definitions (Settings) ---

@router.get("/qc-test-definitions", response_model=List[QCTestDefinitionResponse])
def list_qc_test_definitions(
    current_user=Depends(require_permission("settings", "read")),
    db: Session = Depends(get_db),
):
    return db.query(QCTestDefinition).filter(QCTestDefinition.is_active == True).all()


@router.get("/qc-test-definitions/all", response_model=List[QCTestDefinitionResponse])
def list_all_qc_test_definitions(
    current_user=Depends(require_permission("settings", "read")),
    db: Session = Depends(get_db),
):
    return db.query(QCTestDefinition).all()


@router.post("/qc-test-definitions", response_model=QCTestDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_qc_test_definition(
    td_in: QCTestDefinitionCreate,
    current_user=Depends(require_permission("settings", "create")),
    db: Session = Depends(get_db),
):
    td = QCTestDefinition(**td_in.model_dump())
    db.add(td)
    db.commit()
    db.refresh(td)
    return td


@router.put("/qc-test-definitions/{td_id}", response_model=QCTestDefinitionResponse)
def update_qc_test_definition(
    td_id: int, td_in: QCTestDefinitionUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    td = db.query(QCTestDefinition).filter(QCTestDefinition.id == td_id).first()
    if not td:
        raise HTTPException(status_code=404, detail="QC test definition not found")
    for k, v in td_in.model_dump(exclude_unset=True).items():
        setattr(td, k, v)
    db.commit()
    db.refresh(td)
    return td


@router.delete("/qc-test-definitions/{td_id}")
def delete_qc_test_definition(
    td_id: int,
    current_user=Depends(require_permission("settings", "delete")),
    db: Session = Depends(get_db),
):
    td = db.query(QCTestDefinition).filter(QCTestDefinition.id == td_id).first()
    if not td:
        raise HTTPException(status_code=404, detail="QC test definition not found")
    td.is_active = False
    db.commit()
    return {"detail": "QC test definition deactivated"}


# --- Pack Extension Definitions (Settings) ---

@router.get("/pack-extension-definitions", response_model=List[PackExtensionDefinitionResponse])
def list_pack_extension_definitions(
    current_user=Depends(require_permission("settings", "read")),
    db: Session = Depends(get_db),
):
    return db.query(PackExtensionDefinition).filter(PackExtensionDefinition.is_active == True).all()


@router.post("/pack-extension-definitions", response_model=PackExtensionDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_pack_extension_definition(
    pe_in: PackExtensionDefinitionCreate,
    current_user=Depends(require_permission("settings", "create")),
    db: Session = Depends(get_db),
):
    if db.query(PackExtensionDefinition).filter(PackExtensionDefinition.code == pe_in.code).first():
        raise HTTPException(status_code=400, detail="Pack extension code already exists")
    pe = PackExtensionDefinition(code=pe_in.code, name=pe_in.name, description=pe_in.description)
    for m in pe_in.materials:
        mat = PackExtensionMaterial(**m.model_dump())
        pe.materials.append(mat)
    db.add(pe)
    db.commit()
    db.refresh(pe)
    return pe


@router.put("/pack-extension-definitions/{pe_id}", response_model=PackExtensionDefinitionResponse)
def update_pack_extension_definition(
    pe_id: int, pe_in: PackExtensionDefinitionUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    pe = db.query(PackExtensionDefinition).filter(PackExtensionDefinition.id == pe_id).first()
    if not pe:
        raise HTTPException(status_code=404, detail="Pack extension definition not found")
    if pe_in.name is not None:
        pe.name = pe_in.name
    if pe_in.description is not None:
        pe.description = pe_in.description
    if pe_in.is_active is not None:
        pe.is_active = pe_in.is_active
    if pe_in.materials is not None:
        db.query(PackExtensionMaterial).filter(PackExtensionMaterial.pack_extension_id == pe_id).delete()
        for m in pe_in.materials:
            mat = PackExtensionMaterial(pack_extension_id=pe_id, **m.model_dump())
            db.add(mat)
    db.commit()
    db.refresh(pe)
    return pe


@router.delete("/pack-extension-definitions/{pe_id}")
def delete_pack_extension_definition(
    pe_id: int,
    current_user=Depends(require_permission("settings", "delete")),
    db: Session = Depends(get_db),
):
    pe = db.query(PackExtensionDefinition).filter(PackExtensionDefinition.id == pe_id).first()
    if not pe:
        raise HTTPException(status_code=404, detail="Pack extension definition not found")
    pe.is_active = False
    db.commit()
    return {"detail": "Pack extension definition deactivated"}


# --- Item Pack Extensions ---

@router.get("/items/{item_id}/pack-extensions", response_model=List[ItemPackExtensionResponse])
def list_item_pack_extensions(
    item_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.query(ItemPackExtension).filter(ItemPackExtension.item_id == item_id).all()


@router.post("/items/{item_id}/pack-extensions", response_model=ItemPackExtensionResponse, status_code=status.HTTP_201_CREATED)
def add_item_pack_extension(
    item_id: int, pe_in: ItemPackExtensionCreate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    existing = db.query(ItemPackExtension).filter(
        ItemPackExtension.item_id == item_id,
        ItemPackExtension.pack_extension_id == pe_in.pack_extension_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Pack extension already assigned to this item")
    ipe = ItemPackExtension(item_id=item_id, **pe_in.model_dump())
    db.add(ipe)
    db.commit()
    db.refresh(ipe)
    return ipe


@router.put("/items/{item_id}/pack-extensions/{ipe_id}", response_model=ItemPackExtensionResponse)
def update_item_pack_extension(
    item_id: int, ipe_id: int, pe_in: ItemPackExtensionUpdate,
    current_user=Depends(require_permission("inventory", "update")),
    db: Session = Depends(get_db),
):
    ipe = db.query(ItemPackExtension).filter(
        ItemPackExtension.id == ipe_id, ItemPackExtension.item_id == item_id
    ).first()
    if not ipe:
        raise HTTPException(status_code=404, detail="Item pack extension not found")
    for k, v in pe_in.model_dump(exclude_unset=True).items():
        setattr(ipe, k, v)
    db.commit()
    db.refresh(ipe)
    return ipe


@router.delete("/items/{item_id}/pack-extensions/{ipe_id}")
def remove_item_pack_extension(
    item_id: int, ipe_id: int,
    current_user=Depends(require_permission("inventory", "delete")),
    db: Session = Depends(get_db),
):
    ipe = db.query(ItemPackExtension).filter(
        ItemPackExtension.id == ipe_id, ItemPackExtension.item_id == item_id
    ).first()
    if not ipe:
        raise HTTPException(status_code=404, detail="Item pack extension not found")
    db.delete(ipe)
    db.commit()
    return {"detail": "Pack extension removed from item"}
