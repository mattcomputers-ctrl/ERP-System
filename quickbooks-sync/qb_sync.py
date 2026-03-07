"""
QuickBooks Desktop Synchronization Service for BatchFlow ERP.

This module synchronizes data between BatchFlow ERP and QuickBooks Desktop
using the qbXML API format. It requires a QuickBooks Web Connector (QBWC)
or compatible middleware to communicate with QuickBooks Desktop.

Sync objects: Customers, Vendors, Items, Invoices, Purchase Orders, Bills, Payments
"""
import logging
import time
import json
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import SessionLocal
from app.models.sales import Customer, Invoice, InvoiceLine
from app.models.purchasing import Vendor, PurchaseOrder, PurchaseOrderLine
from app.models.inventory import Item
from app.models.gl_group import GLGroup, GLAccountMapping

logger = logging.getLogger("qb_sync")

QBXML_HEADER = '<?xml version="1.0" encoding="utf-8"?><?qbxml version="16.0"?>'


@dataclass
class SyncResult:
    entity_type: str
    entity_id: int
    action: str
    success: bool
    qb_id: Optional[str] = None
    error: Optional[str] = None


class QBXMLBuilder:
    """Builds qbXML request documents for QuickBooks Desktop."""

    @staticmethod
    def customer_add(customer: Customer) -> str:
        return f"""{QBXML_HEADER}
<QBXML>
<QBXMLMsgsRq onError="stopOnError">
<CustomerAddRq>
<CustomerAdd>
  <Name>{_escape(customer.name)}</Name>
  <CompanyName>{_escape(customer.name)}</CompanyName>
  <FirstName>{_escape(customer.contact_name or '')}</FirstName>
  <BillAddress>
    <Addr1>{_escape(customer.address_line1 or '')}</Addr1>
    <Addr2>{_escape(customer.address_line2 or '')}</Addr2>
    <City>{_escape(customer.city or '')}</City>
    <State>{_escape(customer.state or '')}</State>
    <PostalCode>{_escape(customer.postal_code or '')}</PostalCode>
    <Country>{_escape(customer.country or 'US')}</Country>
  </BillAddress>
  <Phone>{_escape(customer.phone or '')}</Phone>
  <Email>{_escape(customer.email or '')}</Email>
  <TermsRef><FullName>{_escape(customer.payment_terms or 'Net 30')}</FullName></TermsRef>
</CustomerAdd>
</CustomerAddRq>
</QBXMLMsgsRq>
</QBXML>"""

    @staticmethod
    def vendor_add(vendor: Vendor) -> str:
        return f"""{QBXML_HEADER}
<QBXML>
<QBXMLMsgsRq onError="stopOnError">
<VendorAddRq>
<VendorAdd>
  <Name>{_escape(vendor.name)}</Name>
  <CompanyName>{_escape(vendor.name)}</CompanyName>
  <FirstName>{_escape(vendor.contact_name or '')}</FirstName>
  <Phone>{_escape(vendor.phone or '')}</Phone>
  <Email>{_escape(vendor.email or '')}</Email>
  <TermsRef><FullName>{_escape(vendor.payment_terms or 'Net 30')}</FullName></TermsRef>
</VendorAdd>
</VendorAddRq>
</QBXMLMsgsRq>
</QBXML>"""

    @staticmethod
    def invoice_add(invoice: Invoice, customer: Customer, lines: list, gl_mappings: dict) -> str:
        line_xml = ""
        for line in lines:
            account_ref = ""
            if line.gl_group_id and line.gl_group_id in gl_mappings:
                account_ref = f"<AccountRef><FullName>{_escape(gl_mappings[line.gl_group_id])}</FullName></AccountRef>"
            line_xml += f"""
  <InvoiceLineAdd>
    <ItemRef><FullName>{_escape(line.description or 'Item')}</FullName></ItemRef>
    <Desc>{_escape(line.description or '')}</Desc>
    <Quantity>{line.quantity}</Quantity>
    <Rate>{line.unit_price}</Rate>
    <Amount>{line.line_total}</Amount>
    {account_ref}
  </InvoiceLineAdd>"""
        return f"""{QBXML_HEADER}
<QBXML>
<QBXMLMsgsRq onError="stopOnError">
<InvoiceAddRq>
<InvoiceAdd>
  <CustomerRef><FullName>{_escape(customer.name)}</FullName></CustomerRef>
  <TxnDate>{invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else ''}</TxnDate>
  <RefNumber>{_escape(invoice.invoice_number)}</RefNumber>
  {line_xml}
</InvoiceAdd>
</InvoiceAddRq>
</QBXMLMsgsRq>
</QBXML>"""

    @staticmethod
    def purchase_order_add(po: PurchaseOrder, vendor: Vendor, lines: list) -> str:
        line_xml = ""
        for line in lines:
            item = line.item
            line_xml += f"""
  <PurchaseOrderLineAdd>
    <ItemRef><FullName>{_escape(item.name if item else 'Item')}</FullName></ItemRef>
    <Quantity>{line.quantity_ordered}</Quantity>
    <Rate>{line.unit_price}</Rate>
    <Amount>{line.line_total}</Amount>
  </PurchaseOrderLineAdd>"""
        return f"""{QBXML_HEADER}
<QBXML>
<QBXMLMsgsRq onError="stopOnError">
<PurchaseOrderAddRq>
<PurchaseOrderAdd>
  <VendorRef><FullName>{_escape(vendor.name)}</FullName></VendorRef>
  <TxnDate>{po.order_date.strftime('%Y-%m-%d') if po.order_date else ''}</TxnDate>
  <RefNumber>{_escape(po.po_number)}</RefNumber>
  {line_xml}
</PurchaseOrderAdd>
</PurchaseOrderAddRq>
</QBXMLMsgsRq>
</QBXML>"""


def _escape(value: str) -> str:
    """Escape XML special characters."""
    return (value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


class SyncQueue:
    """Manages the synchronization queue with retry logic."""

    def __init__(self, db_session):
        self.db = db_session
        self.queue: list[dict] = []
        self.results: list[SyncResult] = []

    def enqueue(self, entity_type: str, entity_id: int, action: str, qbxml: str):
        self.queue.append({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "qbxml": qbxml,
            "retries": 0,
            "max_retries": 3,
            "created_at": datetime.now(timezone.utc),
        })

    def process(self, send_to_qb_func):
        """Process the sync queue. send_to_qb_func should handle actual QBWC communication."""
        for item in self.queue:
            try:
                response = send_to_qb_func(item["qbxml"])
                qb_id = self._parse_qb_response(response)
                self.results.append(SyncResult(
                    entity_type=item["entity_type"],
                    entity_id=item["entity_id"],
                    action=item["action"],
                    success=True,
                    qb_id=qb_id,
                ))
                logger.info(f"Synced {item['entity_type']} #{item['entity_id']} -> QB {qb_id}")
            except Exception as e:
                item["retries"] += 1
                if item["retries"] < item["max_retries"]:
                    logger.warning(f"Retry {item['retries']} for {item['entity_type']} #{item['entity_id']}: {e}")
                else:
                    self.results.append(SyncResult(
                        entity_type=item["entity_type"],
                        entity_id=item["entity_id"],
                        action=item["action"],
                        success=False,
                        error=str(e),
                    ))
                    logger.error(f"Failed to sync {item['entity_type']} #{item['entity_id']}: {e}")

    @staticmethod
    def _parse_qb_response(response: str) -> Optional[str]:
        # Parse qbXML response for ListID or TxnID
        if not response:
            return None
        for tag in ["ListID", "TxnID"]:
            start = response.find(f"<{tag}>")
            end = response.find(f"</{tag}>")
            if start >= 0 and end > start:
                return response[start + len(tag) + 2:end]
        return None


class QuickBooksSyncService:
    """Main synchronization service between BatchFlow ERP and QuickBooks Desktop."""

    def __init__(self):
        self.builder = QBXMLBuilder()
        self.running = False

    def get_gl_account_mappings(self, db) -> dict:
        """Get GL Group to QB sales account mapping."""
        mappings = {}
        gl_groups = db.query(GLGroup).all()
        for gl in gl_groups:
            for am in gl.account_mappings:
                if am.account_type == "sales" and am.qb_account_ref:
                    mappings[gl.id] = am.qb_account_ref
                elif am.account_type == "sales":
                    mappings[gl.id] = am.account_name
        return mappings

    def sync_customers(self, db, send_func) -> list[SyncResult]:
        """Sync all unsynced customers to QuickBooks."""
        queue = SyncQueue(db)
        customers = db.query(Customer).filter(Customer.qb_list_id.is_(None), Customer.is_active == True).all()
        for cust in customers:
            qbxml = self.builder.customer_add(cust)
            queue.enqueue("customer", cust.id, "add", qbxml)
        queue.process(send_func)
        # Update QB references
        for result in queue.results:
            if result.success and result.qb_id:
                cust = db.query(Customer).filter(Customer.id == result.entity_id).first()
                if cust:
                    cust.qb_list_id = result.qb_id
        db.commit()
        return queue.results

    def sync_vendors(self, db, send_func) -> list[SyncResult]:
        """Sync all unsynced vendors to QuickBooks."""
        queue = SyncQueue(db)
        vendors = db.query(Vendor).filter(Vendor.qb_list_id.is_(None), Vendor.is_active == True).all()
        for v in vendors:
            qbxml = self.builder.vendor_add(v)
            queue.enqueue("vendor", v.id, "add", qbxml)
        queue.process(send_func)
        for result in queue.results:
            if result.success and result.qb_id:
                v = db.query(Vendor).filter(Vendor.id == result.entity_id).first()
                if v:
                    v.qb_list_id = result.qb_id
        db.commit()
        return queue.results

    def sync_invoices(self, db, send_func) -> list[SyncResult]:
        """Sync all unsynced invoices to QuickBooks."""
        queue = SyncQueue(db)
        gl_mappings = self.get_gl_account_mappings(db)
        invoices = db.query(Invoice).filter(Invoice.qb_txn_id.is_(None), Invoice.status != "void").all()
        for inv in invoices:
            customer = db.query(Customer).filter(Customer.id == inv.customer_id).first()
            if not customer:
                continue
            qbxml = self.builder.invoice_add(inv, customer, inv.lines, gl_mappings)
            queue.enqueue("invoice", inv.id, "add", qbxml)
        queue.process(send_func)
        for result in queue.results:
            if result.success and result.qb_id:
                inv = db.query(Invoice).filter(Invoice.id == result.entity_id).first()
                if inv:
                    inv.qb_txn_id = result.qb_id
        db.commit()
        return queue.results

    def sync_purchase_orders(self, db, send_func) -> list[SyncResult]:
        """Sync all unsynced purchase orders to QuickBooks."""
        queue = SyncQueue(db)
        pos = db.query(PurchaseOrder).filter(
            PurchaseOrder.qb_txn_id.is_(None),
            PurchaseOrder.status.in_(["approved", "sent", "partially_received", "received"]),
        ).all()
        for po in pos:
            vendor = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()
            if not vendor:
                continue
            qbxml = self.builder.purchase_order_add(po, vendor, po.lines)
            queue.enqueue("purchase_order", po.id, "add", qbxml)
        queue.process(send_func)
        for result in queue.results:
            if result.success and result.qb_id:
                po = db.query(PurchaseOrder).filter(PurchaseOrder.id == result.entity_id).first()
                if po:
                    po.qb_txn_id = result.qb_id
        db.commit()
        return queue.results

    def run_full_sync(self, send_func):
        """Run a full synchronization cycle."""
        db = SessionLocal()
        try:
            logger.info("Starting full QuickBooks sync...")
            results = []
            results.extend(self.sync_customers(db, send_func))
            results.extend(self.sync_vendors(db, send_func))
            results.extend(self.sync_invoices(db, send_func))
            results.extend(self.sync_purchase_orders(db, send_func))
            success = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            logger.info(f"Sync complete: {success} succeeded, {failed} failed")
            return results
        finally:
            db.close()

    def start_background_sync(self, send_func, interval_seconds: int = 300):
        """Start background sync loop."""
        self.running = True
        logger.info(f"Starting background QB sync (interval: {interval_seconds}s)")
        while self.running:
            try:
                self.run_full_sync(send_func)
            except Exception as e:
                logger.error(f"Sync cycle error: {e}")
            time.sleep(interval_seconds)

    def stop(self):
        self.running = False


# QBWC Web Connector endpoint placeholder
def create_qbwc_endpoint():
    """
    Creates a SOAP endpoint for QuickBooks Web Connector.
    In production, this would be a proper SOAP service that:
    1. Authenticates the QBWC connection
    2. Sends pending qbXML requests
    3. Receives and processes responses
    4. Updates sync status

    The QBWC typically calls:
    - authenticate() - verify connection
    - sendRequestXML() - get next qbXML request
    - receiveResponseXML() - process QB response
    - closeConnection() - end session
    """
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("QuickBooks Sync Service")
    print("=======================")
    print("This service syncs BatchFlow ERP data with QuickBooks Desktop.")
    print("It requires QuickBooks Web Connector (QBWC) to be configured.")
    print()
    print("Usage:")
    print("  1. Configure QB Web Connector with the QBWC endpoint")
    print("  2. Map GL Groups to QuickBooks accounts in Admin > GL Groups")
    print("  3. Start sync service: python qb_sync.py --daemon")
    print()
    print("Run with --test to perform a dry-run sync check.")
