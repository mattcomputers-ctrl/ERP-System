"""
QuickBooks Enterprise synchronization API routes.
Provides endpoints for managing QB sync status, triggering syncs,
and configuring GL account mappings.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.core.config import settings
from app.models.sales import Customer, Invoice, InvoiceLine
from app.models.purchasing import Vendor, PurchaseOrder, PurchaseOrderLine
from app.models.inventory import Item
from app.models.gl_group import GLGroup, GLAccountMapping

logger = logging.getLogger("quickbooks")

router = APIRouter(prefix="/quickbooks", tags=["QuickBooks Sync"])

# In-memory sync state
_sync_state = {
    "last_sync": None,
    "is_running": False,
    "last_results": [],
}

QBXML_HEADER = '<?xml version="1.0" encoding="utf-8"?><?qbxml version="16.0"?>'


def _escape(value: str) -> str:
    return (value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def _build_customer_qbxml(customer: Customer) -> str:
    addr1 = customer.billing_address_line1 or customer.address_line1 or ""
    addr2 = customer.billing_address_line2 or customer.address_line2 or ""
    city = customer.billing_city or customer.city or ""
    state_val = customer.billing_state or customer.state or ""
    postal = customer.billing_postal_code or customer.postal_code or ""
    return f"""{QBXML_HEADER}
<QBXML><QBXMLMsgsRq onError="stopOnError">
<CustomerAddRq><CustomerAdd>
  <Name>{_escape(customer.name)}</Name>
  <CompanyName>{_escape(customer.name)}</CompanyName>
  <FirstName>{_escape(customer.contact_name or '')}</FirstName>
  <BillAddress>
    <Addr1>{_escape(addr1)}</Addr1><Addr2>{_escape(addr2)}</Addr2>
    <City>{_escape(city)}</City><State>{_escape(state_val)}</State>
    <PostalCode>{_escape(postal)}</PostalCode>
  </BillAddress>
  <Phone>{_escape(customer.phone or '')}</Phone>
  <Email>{_escape(customer.email or '')}</Email>
  <TermsRef><FullName>{_escape(customer.payment_terms or 'Net 30')}</FullName></TermsRef>
</CustomerAdd></CustomerAddRq>
</QBXMLMsgsRq></QBXML>"""


def _build_vendor_qbxml(vendor: Vendor) -> str:
    return f"""{QBXML_HEADER}
<QBXML><QBXMLMsgsRq onError="stopOnError">
<VendorAddRq><VendorAdd>
  <Name>{_escape(vendor.name)}</Name>
  <CompanyName>{_escape(vendor.name)}</CompanyName>
  <FirstName>{_escape(vendor.contact_name or '')}</FirstName>
  <Phone>{_escape(vendor.phone or '')}</Phone>
  <Email>{_escape(vendor.email or '')}</Email>
  <TermsRef><FullName>{_escape(vendor.payment_terms or 'Net 30')}</FullName></TermsRef>
</VendorAdd></VendorAddRq>
</QBXMLMsgsRq></QBXML>"""


def _build_invoice_qbxml(invoice, customer, lines, gl_mappings) -> str:
    line_xml = ""
    for line in lines:
        acct = ""
        if line.gl_group_id and line.gl_group_id in gl_mappings:
            acct = f"<AccountRef><FullName>{_escape(gl_mappings[line.gl_group_id])}</FullName></AccountRef>"
        line_xml += f"""<InvoiceLineAdd>
    <ItemRef><FullName>{_escape(line.description or 'Item')}</FullName></ItemRef>
    <Desc>{_escape(line.description or '')}</Desc>
    <Quantity>{line.quantity}</Quantity><Rate>{line.unit_price}</Rate>
    <Amount>{line.line_total}</Amount>{acct}
  </InvoiceLineAdd>"""
    date_str = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else ''
    return f"""{QBXML_HEADER}
<QBXML><QBXMLMsgsRq onError="stopOnError">
<InvoiceAddRq><InvoiceAdd>
  <CustomerRef><FullName>{_escape(customer.name)}</FullName></CustomerRef>
  <TxnDate>{date_str}</TxnDate>
  <RefNumber>{_escape(invoice.invoice_number)}</RefNumber>
  {line_xml}
</InvoiceAdd></InvoiceAddRq>
</QBXMLMsgsRq></QBXML>"""


def _build_po_qbxml(po, vendor, lines) -> str:
    line_xml = ""
    for line in lines:
        item_name = line.item.name if line.item else "Item"
        line_xml += f"""<PurchaseOrderLineAdd>
    <ItemRef><FullName>{_escape(item_name)}</FullName></ItemRef>
    <Quantity>{line.quantity_ordered}</Quantity><Rate>{line.unit_price}</Rate>
    <Amount>{line.line_total}</Amount>
  </PurchaseOrderLineAdd>"""
    date_str = po.order_date.strftime('%Y-%m-%d') if po.order_date else ''
    return f"""{QBXML_HEADER}
<QBXML><QBXMLMsgsRq onError="stopOnError">
<PurchaseOrderAddRq><PurchaseOrderAdd>
  <VendorRef><FullName>{_escape(vendor.name)}</FullName></VendorRef>
  <TxnDate>{date_str}</TxnDate>
  <RefNumber>{_escape(po.po_number)}</RefNumber>
  {line_xml}
</PurchaseOrderAdd></PurchaseOrderAddRq>
</QBXMLMsgsRq></QBXML>"""


def _run_sync(db: Session):
    """Execute a full sync cycle. In production, this sends qbXML to QBWC."""
    results = []
    gl_mappings = {}
    for gl in db.query(GLGroup).all():
        for am in gl.account_mappings:
            if am.account_type == "sales":
                gl_mappings[gl.id] = am.qb_account_ref or am.account_name

    # Sync customers
    unsync_customers = db.query(Customer).filter(Customer.qb_list_id.is_(None), Customer.is_active == True).all()
    for c in unsync_customers:
        qbxml = _build_customer_qbxml(c)
        results.append({"entity": "customer", "id": c.id, "name": c.name, "qbxml_generated": True, "action": "add"})

    # Sync vendors
    unsync_vendors = db.query(Vendor).filter(Vendor.qb_list_id.is_(None), Vendor.is_active == True).all()
    for v in unsync_vendors:
        qbxml = _build_vendor_qbxml(v)
        results.append({"entity": "vendor", "id": v.id, "name": v.name, "qbxml_generated": True, "action": "add"})

    # Sync invoices
    unsync_invoices = db.query(Invoice).filter(Invoice.qb_txn_id.is_(None), Invoice.status != "void").all()
    for inv in unsync_invoices:
        customer = db.query(Customer).filter(Customer.id == inv.customer_id).first()
        if customer:
            qbxml = _build_invoice_qbxml(inv, customer, inv.lines, gl_mappings)
            results.append({"entity": "invoice", "id": inv.id, "number": inv.invoice_number, "qbxml_generated": True, "action": "add"})

    # Sync POs
    unsync_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.qb_txn_id.is_(None),
        PurchaseOrder.status.in_(["approved", "sent", "partially_received", "received"]),
    ).all()
    for po in unsync_pos:
        vendor = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()
        if vendor:
            qbxml = _build_po_qbxml(po, vendor, po.lines)
            results.append({"entity": "purchase_order", "id": po.id, "number": po.po_number, "qbxml_generated": True, "action": "add"})

    return results


# --- API Endpoints ---

@router.get("/status")
def get_sync_status(current_user=Depends(get_current_user)):
    return {
        "enabled": settings.QB_SYNC_ENABLED,
        "interval_seconds": settings.QB_SYNC_INTERVAL_SECONDS,
        "is_running": _sync_state["is_running"],
        "last_sync": _sync_state["last_sync"],
        "last_result_count": len(_sync_state["last_results"]),
    }


@router.get("/pending")
def get_pending_sync(
    current_user=Depends(require_permission("quickbooks", "read")),
    db: Session = Depends(get_db),
):
    """Get counts of records pending sync to QuickBooks."""
    customers = db.query(Customer).filter(Customer.qb_list_id.is_(None), Customer.is_active == True).count()
    vendors = db.query(Vendor).filter(Vendor.qb_list_id.is_(None), Vendor.is_active == True).count()
    invoices = db.query(Invoice).filter(Invoice.qb_txn_id.is_(None), Invoice.status != "void").count()
    pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.qb_txn_id.is_(None),
        PurchaseOrder.status.in_(["approved", "sent", "partially_received", "received"]),
    ).count()
    return {
        "customers": customers,
        "vendors": vendors,
        "invoices": invoices,
        "purchase_orders": pos,
        "total": customers + vendors + invoices + pos,
    }


@router.post("/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user=Depends(require_permission("quickbooks", "create")),
    db: Session = Depends(get_db),
):
    """Trigger a manual sync cycle. Generates qbXML for all unsynced records."""
    if _sync_state["is_running"]:
        raise HTTPException(status_code=409, detail="Sync is already running")

    _sync_state["is_running"] = True
    try:
        results = _run_sync(db)
        _sync_state["last_sync"] = datetime.now(timezone.utc).isoformat()
        _sync_state["last_results"] = results
        return {
            "detail": "Sync completed",
            "records_processed": len(results),
            "results": results,
        }
    finally:
        _sync_state["is_running"] = False


@router.get("/sync/results")
def get_last_sync_results(current_user=Depends(require_permission("quickbooks", "read"))):
    return {
        "last_sync": _sync_state["last_sync"],
        "results": _sync_state["last_results"],
    }


@router.get("/qbxml/preview/{entity_type}/{entity_id}")
def preview_qbxml(
    entity_type: str,
    entity_id: int,
    current_user=Depends(require_permission("quickbooks", "read")),
    db: Session = Depends(get_db),
):
    """Preview the qbXML that would be sent for a specific entity."""
    if entity_type == "customer":
        obj = db.query(Customer).filter(Customer.id == entity_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"qbxml": _build_customer_qbxml(obj)}

    elif entity_type == "vendor":
        obj = db.query(Vendor).filter(Vendor.id == entity_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return {"qbxml": _build_vendor_qbxml(obj)}

    elif entity_type == "invoice":
        inv = db.query(Invoice).filter(Invoice.id == entity_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        customer = db.query(Customer).filter(Customer.id == inv.customer_id).first()
        gl_mappings = {}
        for gl in db.query(GLGroup).all():
            for am in gl.account_mappings:
                if am.account_type == "sales":
                    gl_mappings[gl.id] = am.qb_account_ref or am.account_name
        return {"qbxml": _build_invoice_qbxml(inv, customer, inv.lines, gl_mappings)}

    elif entity_type == "purchase_order":
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == entity_id).first()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        vendor = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()
        return {"qbxml": _build_po_qbxml(po, vendor, po.lines)}

    raise HTTPException(status_code=400, detail=f"Unsupported entity type: {entity_type}")
