from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from typing import Optional
from decimal import Decimal
from io import BytesIO
import csv
import io
from app.core.database import get_db
from app.core.security import require_permission
from app.models.inventory import Item, Lot, FIFOCostLayer, InventoryTransaction
from app.models.sales import SalesOrder, SalesOrderLine, Customer, Invoice
from app.models.purchasing import PurchaseOrder, PurchaseOrderLine, Vendor
from app.models.manufacturing import ProductionOrder, Formula
from app.models.quality import QCResult, QCTest, QCSpecification
from app.models.gl_group import GLGroup

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/inventory/by-lot")
def inventory_by_lot(
    item_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(Lot).filter(Lot.quantity_on_hand > 0)
    if item_id:
        q = q.filter(Lot.item_id == item_id)
    if warehouse_id:
        q = q.filter(Lot.warehouse_id == warehouse_id)
    lots = q.all()
    result = []
    for lot in lots:
        item = db.query(Item).filter(Item.id == lot.item_id).first()
        result.append({
            "lot_number": lot.lot_number,
            "item_code": item.item_code if item else None,
            "item_name": item.name if item else None,
            "quantity_on_hand": float(lot.quantity_on_hand),
            "quantity_allocated": float(lot.quantity_allocated),
            "status": lot.status,
            "warehouse_id": lot.warehouse_id,
            "expiration_date": lot.expiration_date.isoformat() if lot.expiration_date else None,
            "received_date": lot.received_date.isoformat() if lot.received_date else None,
        })
    return result


@router.get("/inventory/fifo-valuation")
def fifo_valuation_report(
    gl_group_id: Optional[int] = None,
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(FIFOCostLayer).filter(FIFOCostLayer.quantity_remaining > 0)
    layers = q.order_by(FIFOCostLayer.item_id, FIFOCostLayer.received_date).all()
    items_summary = {}
    for layer in layers:
        item = db.query(Item).filter(Item.id == layer.item_id).first()
        if gl_group_id and item and item.gl_group_id != gl_group_id:
            continue
        key = layer.item_id
        if key not in items_summary:
            items_summary[key] = {
                "item_id": layer.item_id,
                "item_code": item.item_code if item else None,
                "item_name": item.name if item else None,
                "gl_group_id": item.gl_group_id if item else None,
                "total_quantity": 0,
                "total_value": 0,
                "layers": [],
            }
        qty = float(layer.quantity_remaining)
        val = float(layer.quantity_remaining * layer.unit_cost)
        items_summary[key]["total_quantity"] += qty
        items_summary[key]["total_value"] += val
        items_summary[key]["layers"].append({
            "quantity": qty,
            "unit_cost": float(layer.unit_cost),
            "value": val,
            "date": layer.received_date.isoformat() if layer.received_date else None,
        })
    return list(items_summary.values())


@router.get("/inventory/by-gl-group")
def inventory_by_gl_group(
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    layers = db.query(FIFOCostLayer).filter(FIFOCostLayer.quantity_remaining > 0).all()
    groups = {}
    for layer in layers:
        item = db.query(Item).filter(Item.id == layer.item_id).first()
        gl_id = item.gl_group_id if item else None
        if gl_id not in groups:
            gl = db.query(GLGroup).filter(GLGroup.id == gl_id).first() if gl_id else None
            groups[gl_id] = {
                "gl_group_id": gl_id,
                "gl_group_name": gl.name if gl else "Unassigned",
                "total_quantity": 0,
                "total_value": 0,
                "item_count": 0,
            }
        groups[gl_id]["total_quantity"] += float(layer.quantity_remaining)
        groups[gl_id]["total_value"] += float(layer.quantity_remaining * layer.unit_cost)
    for g in groups.values():
        g["item_count"] = db.query(Item).filter(Item.gl_group_id == g["gl_group_id"]).count() if g["gl_group_id"] else 0
    return list(groups.values())


@router.get("/manufacturing/batch-history")
def batch_history_report(
    status_filter: Optional[str] = None,
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(ProductionOrder)
    if status_filter:
        q = q.filter(ProductionOrder.status == status_filter)
    orders = q.order_by(ProductionOrder.created_at.desc()).limit(200).all()
    result = []
    for po in orders:
        formula = db.query(Formula).filter(Formula.id == po.formula_id).first()
        result.append({
            "order_number": po.order_number,
            "formula": formula.name if formula else None,
            "planned_quantity": float(po.planned_quantity),
            "actual_quantity": float(po.actual_quantity) if po.actual_quantity else None,
            "yield_percent": float(po.yield_percent) if po.yield_percent else None,
            "status": po.status,
            "start_date": po.actual_start_date.isoformat() if po.actual_start_date else None,
            "end_date": po.actual_end_date.isoformat() if po.actual_end_date else None,
        })
    return result


@router.get("/quality/results-by-lot")
def qc_results_by_lot(
    lot_id: Optional[int] = None,
    passed: Optional[bool] = None,
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(QCResult)
    if lot_id:
        q = q.filter(QCResult.lot_id == lot_id)
    if passed is not None:
        q = q.filter(QCResult.passed == passed)
    results = q.order_by(QCResult.tested_at.desc()).limit(500).all()
    data = []
    for r in results:
        lot = db.query(Lot).filter(Lot.id == r.lot_id).first()
        test = db.query(QCTest).filter(QCTest.id == r.test_id).first()
        data.append({
            "lot_number": lot.lot_number if lot else None,
            "test_name": test.test_name if test else None,
            "result_value": float(r.result_value) if r.result_value else None,
            "passed": r.passed,
            "tested_at": r.tested_at.isoformat() if r.tested_at else None,
        })
    return data


@router.get("/sales/by-customer")
def sales_by_customer(
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    result = []
    for c in customers:
        orders = db.query(SalesOrder).filter(SalesOrder.customer_id == c.id).all()
        total = sum(float(o.total_amount) for o in orders)
        result.append({
            "customer_code": c.code,
            "customer_name": c.name,
            "order_count": len(orders),
            "total_revenue": total,
        })
    return sorted(result, key=lambda x: x["total_revenue"], reverse=True)


@router.get("/sales/by-gl-group")
def sales_by_gl_group(
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    results = db.query(
        GLGroup.name,
        sql_func.sum(SalesOrderLine.line_total),
    ).join(Item, Item.gl_group_id == GLGroup.id
    ).join(SalesOrderLine, SalesOrderLine.item_id == Item.id
    ).group_by(GLGroup.name).all()
    return [{"gl_group": r[0], "total_sales": float(r[1] or 0)} for r in results]


@router.get("/purchasing/by-vendor")
def purchases_by_vendor(
    current_user=Depends(require_permission("reporting", "read")),
    db: Session = Depends(get_db),
):
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    result = []
    for v in vendors:
        orders = db.query(PurchaseOrder).filter(PurchaseOrder.vendor_id == v.id).all()
        total = sum(float(o.total_amount) for o in orders)
        result.append({
            "vendor_code": v.code,
            "vendor_name": v.name,
            "order_count": len(orders),
            "total_purchases": total,
        })
    return sorted(result, key=lambda x: x["total_purchases"], reverse=True)


@router.get("/export/inventory-csv")
def export_inventory_csv(
    current_user=Depends(require_permission("reporting", "export")),
    db: Session = Depends(get_db),
):
    lots = db.query(Lot).filter(Lot.quantity_on_hand > 0).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Lot Number", "Item Code", "Item Name", "Quantity", "Status", "Warehouse", "Expiration"])
    for lot in lots:
        item = db.query(Item).filter(Item.id == lot.item_id).first()
        writer.writerow([
            lot.lot_number,
            item.item_code if item else "",
            item.name if item else "",
            float(lot.quantity_on_hand),
            lot.status,
            lot.warehouse_id or "",
            lot.expiration_date.isoformat() if lot.expiration_date else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_report.csv"},
    )
