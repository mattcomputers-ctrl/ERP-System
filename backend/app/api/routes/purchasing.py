from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.purchasing import Vendor, PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine
from app.models.inventory import Item, Lot, InventoryTransaction, FIFOCostLayer
from app.schemas.purchasing import (
    VendorCreate, VendorUpdate, VendorResponse,
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    ReceiptCreate, ReceiptResponse,
)

router = APIRouter(prefix="/purchasing", tags=["Purchasing"])


# --- Vendors ---

@router.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("purchasing", "read")),
    db: Session = Depends(get_db),
):
    return db.query(Vendor).filter(Vendor.is_active == True).offset(skip).limit(limit).all()


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    v_in: VendorCreate,
    current_user=Depends(require_permission("purchasing", "create")),
    db: Session = Depends(get_db),
):
    if db.query(Vendor).filter(Vendor.code == v_in.code).first():
        raise HTTPException(status_code=400, detail="Vendor code already exists")
    vendor = Vendor(**v_in.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return v


@router.put("/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int, v_in: VendorUpdate,
    current_user=Depends(require_permission("purchasing", "update")),
    db: Session = Depends(get_db),
):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for k, val in v_in.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v


# --- Purchase Orders ---

def _generate_po_number(db: Session) -> str:
    last = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"PO-{num:06d}"


@router.get("/orders", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    status_filter: Optional[str] = None, vendor_id: Optional[int] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("purchasing", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(PurchaseOrder)
    if status_filter:
        q = q.filter(PurchaseOrder.status == status_filter)
    if vendor_id:
        q = q.filter(PurchaseOrder.vendor_id == vendor_id)
    return q.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    po_in: PurchaseOrderCreate,
    current_user=Depends(require_permission("purchasing", "create")),
    db: Session = Depends(get_db),
):
    po = PurchaseOrder(
        po_number=_generate_po_number(db),
        vendor_id=po_in.vendor_id,
        expected_delivery_date=po_in.expected_delivery_date,
        notes=po_in.notes,
        created_by=current_user.id,
    )
    subtotal = 0
    for line_data in po_in.lines:
        line_total = line_data.quantity_ordered * line_data.unit_price
        line = PurchaseOrderLine(
            item_id=line_data.item_id,
            line_number=line_data.line_number,
            quantity_ordered=line_data.quantity_ordered,
            unit_price=line_data.unit_price,
            line_total=line_total,
        )
        po.lines.append(line)
        subtotal += line_total
    po.subtotal = subtotal
    po.total_amount = subtotal
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.get("/orders/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(po_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.put("/orders/{po_id}", response_model=PurchaseOrderResponse)
def update_purchase_order(
    po_id: int, po_in: PurchaseOrderUpdate,
    current_user=Depends(require_permission("purchasing", "update")),
    db: Session = Depends(get_db),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    for k, v in po_in.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    if po_in.status == "approved":
        po.approved_by = current_user.id
        po.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(po)
    return po


# --- Receiving ---

def _generate_receipt_number(db: Session) -> str:
    last = db.query(Receipt).order_by(Receipt.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"RCV-{num:06d}"


@router.post("/receipts", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def receive_purchase_order(
    rcv_in: ReceiptCreate,
    current_user=Depends(require_permission("purchasing", "create")),
    db: Session = Depends(get_db),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == rcv_in.purchase_order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    receipt = Receipt(
        receipt_number=_generate_receipt_number(db),
        purchase_order_id=po.id,
        notes=rcv_in.notes,
        created_by=current_user.id,
    )
    for rl in rcv_in.lines:
        pol = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == rl.purchase_order_line_id).first()
        if not pol:
            continue
        item = db.query(Item).filter(Item.id == rl.item_id).first()
        # Create or find lot
        lot = db.query(Lot).filter(Lot.lot_number == rl.lot_number).first()
        if not lot:
            lot = Lot(
                lot_number=rl.lot_number,
                item_id=rl.item_id,
                warehouse_id=rl.warehouse_id,
                location_id=rl.location_id,
                quantity_on_hand=rl.quantity_received,
                status="on_hold" if rl.qc_hold else "available",
                received_date=datetime.now(timezone.utc),
                vendor_lot_number=rl.vendor_lot_number,
                expiration_date=rl.expiration_date,
            )
            db.add(lot)
            db.flush()
        else:
            lot.quantity_on_hand += rl.quantity_received
            if rl.qc_hold:
                lot.status = "on_hold"
        # Create FIFO cost layer
        layer = FIFOCostLayer(
            item_id=rl.item_id, lot_id=lot.id,
            quantity_remaining=rl.quantity_received,
            unit_cost=pol.unit_price,
            total_cost=pol.unit_price * rl.quantity_received,
            reference_type="purchase_receipt",
        )
        db.add(layer)
        # Update PO line received qty
        pol.quantity_received += rl.quantity_received
        # Create inventory transaction
        txn = InventoryTransaction(
            transaction_type="receipt",
            item_id=rl.item_id, lot_id=lot.id,
            warehouse_id=rl.warehouse_id, location_id=rl.location_id,
            quantity=rl.quantity_received,
            unit_cost=pol.unit_price,
            total_cost=pol.unit_price * rl.quantity_received,
            gl_group_id=item.gl_group_id if item else None,
            reference_type="purchase_receipt",
            created_by=current_user.id,
        )
        db.add(txn)
        receipt_line = ReceiptLine(
            purchase_order_line_id=pol.id,
            item_id=rl.item_id,
            lot_id=lot.id,
            quantity_received=rl.quantity_received,
            warehouse_id=rl.warehouse_id,
            location_id=rl.location_id,
            qc_status="on_hold" if rl.qc_hold else "pending",
        )
        receipt.lines.append(receipt_line)
    # Update PO status
    all_received = all(
        l.quantity_received >= l.quantity_ordered for l in po.lines
    )
    any_received = any(l.quantity_received > 0 for l in po.lines)
    if all_received:
        po.status = "received"
    elif any_received:
        po.status = "partially_received"
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt
