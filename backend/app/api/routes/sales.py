from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.sales import Customer, SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Invoice, InvoiceLine, PackingList
from app.models.inventory import Item, Lot, InventoryTransaction, FIFOCostLayer
from app.models.settings import Branding
from app.schemas.sales import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse,
    ShipmentCreate, ShipmentResponse,
)

router = APIRouter(prefix="/sales", tags=["Sales"])


# --- Customers ---

@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0, limit: int = 100, include_inactive: bool = False,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if not include_inactive:
        q = q.filter(Customer.is_active == True)
    return q.offset(skip).limit(limit).all()


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
        ship_to_id=so_in.ship_to_id,
        ship_via_id=so_in.ship_via_id,
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


# --- Pick List ---

@router.get("/orders/{order_id}/pick-list")
def get_pick_list(
    order_id: int,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    customer = db.query(Customer).filter(Customer.id == so.customer_id).first()
    pick_items = []
    for line in so.lines:
        item = db.query(Item).filter(Item.id == line.item_id).first()
        qty_to_pick = float(line.quantity_ordered) - float(line.quantity_shipped)
        if qty_to_pick <= 0:
            continue
        available_lots = db.query(Lot).filter(
            Lot.item_id == line.item_id,
            Lot.status == "available",
            Lot.quantity_on_hand > 0,
        ).order_by(Lot.received_date).all()
        lot_suggestions = []
        remaining = qty_to_pick
        for lot in available_lots:
            if remaining <= 0:
                break
            pick_qty = min(remaining, float(lot.quantity_on_hand))
            lot_suggestions.append({
                "lot_id": lot.id,
                "lot_number": lot.lot_number,
                "available_qty": float(lot.quantity_on_hand),
                "suggested_pick_qty": pick_qty,
                "warehouse_id": lot.warehouse_id,
                "location_id": lot.location_id,
                "expiration_date": lot.expiration_date.isoformat() if lot.expiration_date else None,
            })
            remaining -= pick_qty
        pick_items.append({
            "line_number": line.line_number,
            "item_id": line.item_id,
            "item_code": item.item_code if item else None,
            "item_name": item.name if item else None,
            "quantity_ordered": float(line.quantity_ordered),
            "quantity_shipped": float(line.quantity_shipped),
            "quantity_to_pick": qty_to_pick,
            "lot_suggestions": lot_suggestions,
        })
    return {
        "order_number": so.order_number,
        "customer_name": customer.name if customer else None,
        "requested_ship_date": so.requested_ship_date.isoformat() if so.requested_ship_date else None,
        "items": pick_items,
    }


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
        if lot_id:
            lot = db.query(Lot).filter(Lot.id == lot_id).first()
            if lot and lot.quantity_on_hand >= qty:
                lot.quantity_on_hand -= qty
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
    customer = db.query(Customer).filter(Customer.id == so.customer_id).first()
    due_date = None
    if customer and customer.payment_terms:
        import re
        match = re.search(r'(\d+)', customer.payment_terms)
        if match:
            from datetime import timedelta
            days = int(match.group(1))
            due_date = datetime.now(timezone.utc) + timedelta(days=days)
    invoice = Invoice(
        invoice_number=inv_num,
        sales_order_id=so.id,
        customer_id=so.customer_id,
        due_date=due_date,
        subtotal=so.subtotal,
        tax_amount=so.tax_amount,
        total_amount=so.total_amount,
    )
    for sol in so.lines:
        item = db.query(Item).filter(Item.id == sol.item_id).first()
        inv_line = InvoiceLine(
            item_id=sol.item_id,
            description=item.name if item else None,
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
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "status": invoice.status,
    }


@router.post("/orders/{order_id}/packing-list")
def create_packing_list(
    order_id: int,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    last_pl = db.query(PackingList).order_by(PackingList.id.desc()).first()
    pl_num = f"PL-{(last_pl.id + 1 if last_pl else 1):06d}"
    customer = db.query(Customer).filter(Customer.id == so.customer_id).first()
    branding = db.query(Branding).first()
    pl = PackingList(packing_list_number=pl_num, sales_order_id=so.id)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    items = []
    for line in so.lines:
        item = db.query(Item).filter(Item.id == line.item_id).first()
        items.append({
            "line_number": line.line_number,
            "item_code": item.item_code if item else None,
            "item_name": item.name if item else None,
            "quantity": float(line.quantity_ordered),
            "quantity_shipped": float(line.quantity_shipped),
        })
    ship_to = None
    if so.ship_to_id:
        from app.models.sales import ShipTo
        st = db.query(ShipTo).filter(ShipTo.id == so.ship_to_id).first()
        if st:
            ship_to = {
                "name": st.name, "address_line1": st.address_line1,
                "city": st.city, "state": st.state, "postal_code": st.postal_code,
            }
    return {
        "id": pl.id, "packing_list_number": pl_num, "order_number": so.order_number,
        "date": datetime.now(timezone.utc).isoformat(),
        "company": {
            "name": branding.company_name, "address_line1": branding.address_line1,
            "city": branding.city, "state": branding.state,
            "postal_code": branding.postal_code, "phone": branding.phone,
        } if branding else None,
        "customer": {"name": customer.name, "code": customer.code} if customer else None,
        "ship_to": ship_to, "items": items,
    }


@router.get("/invoices/{invoice_id}")
def get_invoice_detail(
    invoice_id: int,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()
    branding = db.query(Branding).first()
    lines = []
    for line in invoice.lines:
        item = db.query(Item).filter(Item.id == line.item_id).first()
        lines.append({
            "item_code": item.item_code if item else None,
            "description": line.description or (item.name if item else None),
            "quantity": float(line.quantity), "unit_price": float(line.unit_price),
            "line_total": float(line.line_total),
        })
    return {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "status": invoice.status,
        "company": {
            "name": branding.company_name if branding else "My Company",
            "address_line1": branding.address_line1 if branding else None,
            "city": branding.city if branding else None, "state": branding.state if branding else None,
            "postal_code": branding.postal_code if branding else None,
            "phone": branding.phone if branding else None, "email": branding.email if branding else None,
        },
        "customer": {
            "name": customer.name if customer else None, "code": customer.code if customer else None,
            "billing_address_line1": customer.billing_address_line1 if customer else None,
            "billing_city": customer.billing_city if customer else None,
            "billing_state": customer.billing_state if customer else None,
            "billing_postal_code": customer.billing_postal_code if customer else None,
            "payment_terms": customer.payment_terms if customer else None,
        },
        "lines": lines, "subtotal": float(invoice.subtotal),
        "tax_amount": float(invoice.tax_amount), "total_amount": float(invoice.total_amount),
    }


@router.get("/invoices")
def list_invoices(
    customer_id: Optional[int] = None, status_filter: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("sales", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Invoice)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if status_filter:
        q = q.filter(Invoice.status == status_filter)
    invoices = q.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return [{
        "id": inv.id, "invoice_number": inv.invoice_number,
        "sales_order_id": inv.sales_order_id, "customer_id": inv.customer_id,
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "status": inv.status, "total_amount": float(inv.total_amount),
    } for inv in invoices]
