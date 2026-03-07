from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import require_permission
from app.models.inventory import Lot, Item, InventoryTransaction
from app.models.manufacturing import ProductionOrder, ProductionConsumption, ProductionOutput
from app.models.sales import ShipmentLine, SalesOrder, Customer

router = APIRouter(prefix="/traceability", tags=["Lot Traceability"])


@router.get("/lot/{lot_id}/genealogy")
def get_lot_genealogy(
    lot_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    item = db.query(Item).filter(Item.id == lot.item_id).first()
    result = {
        "lot": {"id": lot.id, "lot_number": lot.lot_number, "item_code": item.item_code if item else None, "item_name": item.name if item else None},
        "sources": _trace_backward(db, lot),
        "destinations": _trace_forward(db, lot),
    }
    return result


def _trace_backward(db: Session, lot: Lot) -> list:
    """Trace a lot back to its raw material sources."""
    sources = []
    # Check if this lot was produced
    output = db.query(ProductionOutput).filter(ProductionOutput.lot_id == lot.id).first()
    if output:
        po = db.query(ProductionOrder).filter(ProductionOrder.id == output.production_order_id).first()
        if po:
            for c in po.consumptions:
                if c.lot_id:
                    src_lot = db.query(Lot).filter(Lot.id == c.lot_id).first()
                    src_item = db.query(Item).filter(Item.id == c.item_id).first()
                    source = {
                        "lot_id": c.lot_id,
                        "lot_number": src_lot.lot_number if src_lot else None,
                        "item_code": src_item.item_code if src_item else None,
                        "item_name": src_item.name if src_item else None,
                        "quantity_used": float(c.actual_quantity) if c.actual_quantity else None,
                        "production_order": po.order_number,
                    }
                    # Recursive trace
                    if src_lot:
                        source["sources"] = _trace_backward(db, src_lot)
                    sources.append(source)
    # Check receipt transactions
    receipts = db.query(InventoryTransaction).filter(
        InventoryTransaction.lot_id == lot.id,
        InventoryTransaction.transaction_type == "receipt",
    ).all()
    for r in receipts:
        sources.append({
            "type": "purchase_receipt",
            "transaction_id": r.id,
            "quantity": float(r.quantity),
            "date": r.created_at.isoformat() if r.created_at else None,
        })
    return sources


def _trace_forward(db: Session, lot: Lot) -> list:
    """Trace a lot forward to its destinations (products or customers)."""
    destinations = []
    # Check if used in production
    consumptions = db.query(ProductionConsumption).filter(ProductionConsumption.lot_id == lot.id).all()
    for c in consumptions:
        po = db.query(ProductionOrder).filter(ProductionOrder.id == c.production_order_id).first()
        if po and po.output_lot_id:
            out_lot = db.query(Lot).filter(Lot.id == po.output_lot_id).first()
            out_item = db.query(Item).filter(Item.id == out_lot.item_id).first() if out_lot else None
            dest = {
                "type": "production",
                "production_order": po.order_number,
                "output_lot_id": po.output_lot_id,
                "output_lot_number": out_lot.lot_number if out_lot else None,
                "output_item": out_item.name if out_item else None,
                "quantity_used": float(c.actual_quantity) if c.actual_quantity else None,
            }
            if out_lot:
                dest["destinations"] = _trace_forward(db, out_lot)
            destinations.append(dest)
    # Check shipments
    ship_lines = db.query(ShipmentLine).filter(ShipmentLine.lot_id == lot.id).all()
    for sl in ship_lines:
        shipment = sl.shipment
        so = db.query(SalesOrder).filter(SalesOrder.id == shipment.sales_order_id).first() if shipment else None
        customer = db.query(Customer).filter(Customer.id == so.customer_id).first() if so else None
        destinations.append({
            "type": "shipment",
            "shipment_number": shipment.shipment_number if shipment else None,
            "customer": customer.name if customer else None,
            "quantity_shipped": float(sl.quantity_shipped),
            "ship_date": shipment.ship_date.isoformat() if shipment and shipment.ship_date else None,
        })
    return destinations


@router.get("/lot/{lot_id}/recall-impact")
def get_recall_impact(
    lot_id: int,
    current_user=Depends(require_permission("inventory", "read")),
    db: Session = Depends(get_db),
):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    affected_customers = set()
    affected_lots = set()
    _collect_impact(db, lot, affected_customers, affected_lots)
    return {
        "source_lot": lot.lot_number,
        "affected_lot_count": len(affected_lots),
        "affected_lots": list(affected_lots),
        "affected_customer_count": len(affected_customers),
        "affected_customers": list(affected_customers),
    }


def _collect_impact(db: Session, lot: Lot, customers: set, lots: set):
    lots.add(lot.lot_number)
    consumptions = db.query(ProductionConsumption).filter(ProductionConsumption.lot_id == lot.id).all()
    for c in consumptions:
        po = db.query(ProductionOrder).filter(ProductionOrder.id == c.production_order_id).first()
        if po and po.output_lot_id:
            out_lot = db.query(Lot).filter(Lot.id == po.output_lot_id).first()
            if out_lot and out_lot.lot_number not in lots:
                _collect_impact(db, out_lot, customers, lots)
    ship_lines = db.query(ShipmentLine).filter(ShipmentLine.lot_id == lot.id).all()
    for sl in ship_lines:
        shipment = sl.shipment
        if shipment:
            so = db.query(SalesOrder).filter(SalesOrder.id == shipment.sales_order_id).first()
            if so:
                cust = db.query(Customer).filter(Customer.id == so.customer_id).first()
                if cust:
                    customers.add(cust.name)
