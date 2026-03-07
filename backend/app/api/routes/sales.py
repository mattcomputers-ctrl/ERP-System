from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.sales import Customer, SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Invoice, InvoiceLine
from app.models.inventory import Item, Lot, InventoryTransaction, FIFOCostLayer
from app.schemas.sales import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse,
    ShipmentCreate, ShipmentResponse,
)

router = APIRouter(prefix="/sales", tags=["Sales"])


# --- Customers ---

@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    return db.query(Customer).filter(Customer.is_active == True).offset(skip).limit(limit).all()


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    cust_in: CustomerCreate,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    if db.query(Customer).filter(Customer.code == cust_in.code).first():
        raise HTTPException(status_code=400, detail="Customer code already exists")
    cust = Customer(**cust_in.model_dump())
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int, cust_in: CustomerUpdate,
    current_user=Depends(require_permission("sales", "update")),
    db: Session = Depends(get_db),
):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    for k, v in cust_in.model_dump(exclude_unset=True).items():
        setattr(cust, k, v)
    db.commit()
    db.refresh(cust)
    return cust


# --- Sales Orders ---

def _generate_so_number(db: Session) -> str:
    last = db.query(SalesOrder).order_by(SalesOrder.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"SO-{num:06d}"


@router.get("/orders", response_model=List[SalesOrderResponse])
def list_sales_orders(
    status_filter: Optional[str] = None, customer_id: Optional[int] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(SalesOrder)
    if status_filter:
        q = q.filter(SalesOrder.status == status_filter)
    if customer_id:
        q = q.filter(SalesOrder.customer_id == customer_id)
    return q.order_by(SalesOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    so_in: SalesOrderCreate,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    so = SalesOrder(
        order_number=_generate_so_number(db),
        customer_id=so_in.customer_id,
        requested_ship_date=so_in.requested_ship_date,
        shipping_method=so_in.shipping_method,
        shipping_address=so_in.shipping_address,
        notes=so_in.notes,
        created_by=current_user.id,
    )
    subtotal = 0
    tax_total = 0
    for line_data in so_in.lines:
        line_total = line_data.quantity_ordered * line_data.unit_price
        tax = line_total * line_data.tax_rate / 100
        line = SalesOrderLine(
            item_id=line_data.item_id,
            line_number=line_data.line_number,
            quantity_ordered=line_data.quantity_ordered,
            unit_price=line_data.unit_price,
            tax_rate=line_data.tax_rate,
            line_total=line_total,
        )
        so.lines.append(line)
        subtotal += line_total
        tax_total += tax
    so.subtotal = subtotal
    so.tax_amount = tax_total
    so.total_amount = subtotal + tax_total
    db.add(so)
    db.commit()
    db.refresh(so)
    return so


@router.get("/orders/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(order_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return so


@router.put("/orders/{order_id}", response_model=SalesOrderResponse)
def update_sales_order(
    order_id: int, so_in: SalesOrderUpdate,
    current_user=Depends(require_permission("sales", "update")),
    db: Session = Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    for k, v in so_in.model_dump(exclude_unset=True).items():
        setattr(so, k, v)
    db.commit()
    db.refresh(so)
    return so


# --- Shipments ---

def _generate_shipment_number(db: Session) -> str:
    last = db.query(Shipment).order_by(Shipment.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"SHP-{num:06d}"


@router.post("/shipments", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(
    ship_in: ShipmentCreate,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == ship_in.sales_order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    shipment = Shipment(
        shipment_number=_generate_shipment_number(db),
        sales_order_id=ship_in.sales_order_id,
        carrier=ship_in.carrier,
        tracking_number=ship_in.tracking_number,
        status="shipped",
        created_by=current_user.id,
    )
    for line_data in ship_in.lines:
        sol = db.query(SalesOrderLine).filter(SalesOrderLine.id == line_data["sales_order_line_id"]).first()
        if not sol:
            continue
        lot_id = line_data.get("lot_id")
        qty = line_data["quantity_shipped"]
        # Update lot inventory
        if lot_id:
            lot = db.query(Lot).filter(Lot.id == lot_id).first()
            if lot and lot.quantity_on_hand >= qty:
                lot.quantity_on_hand -= qty
                # Consume FIFO layers
                remaining = qty
                layers = db.query(FIFOCostLayer).filter(
                    FIFOCostLayer.item_id == sol.item_id,
                    FIFOCostLayer.lot_id == lot_id,
                    FIFOCostLayer.quantity_remaining > 0,
                ).order_by(FIFOCostLayer.received_date).all()
                for layer in layers:
                    if remaining <= 0:
                        break
                    consume = min(remaining, layer.quantity_remaining)
                    layer.quantity_remaining -= consume
                    remaining -= consume
        sol.quantity_shipped += qty
        item = db.query(Item).filter(Item.id == sol.item_id).first()
        ship_line = ShipmentLine(
            sales_order_line_id=sol.id,
            item_id=sol.item_id,
            lot_id=lot_id,
            quantity_shipped=qty,
        )
        shipment.lines.append(ship_line)
        txn = InventoryTransaction(
            transaction_type="shipment",
            item_id=sol.item_id, lot_id=lot_id,
            quantity=-qty,
            gl_group_id=item.gl_group_id if item else None,
            reference_type="shipment",
            created_by=current_user.id,
        )
        db.add(txn)
    so.status = "shipped"
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


# --- Invoices ---

@router.post("/orders/{order_id}/invoice")
def create_invoice_from_order(
    order_id: int,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    last_inv = db.query(Invoice).order_by(Invoice.id.desc()).first()
    inv_num = f"INV-{(last_inv.id + 1 if last_inv else 1):06d}"
    invoice = Invoice(
        invoice_number=inv_num,
        sales_order_id=so.id,
        customer_id=so.customer_id,
        subtotal=so.subtotal,
        tax_amount=so.tax_amount,
        total_amount=so.total_amount,
    )
    for sol in so.lines:
        item = db.query(Item).filter(Item.id == sol.item_id).first()
        inv_line = InvoiceLine(
            item_id=sol.item_id,
            quantity=sol.quantity_ordered,
            unit_price=sol.unit_price,
            line_total=sol.line_total,
            gl_group_id=item.gl_group_id if item else None,
        )
        invoice.lines.append(inv_line)
    so.status = "invoiced"
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "total_amount": float(invoice.total_amount),
        "status": invoice.status,
    }
