from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    # Billing address
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_postal_code = Column(String(20), nullable=True)
    billing_country = Column(String(100), default="US")
    # Legacy columns kept for migration compatibility
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="US")
    payment_terms = Column(String(50), nullable=True)
    credit_limit = Column(Numeric(18, 2), nullable=True)
    sales_rep = Column(String(200), nullable=True)
    default_ship_via_id = Column(Integer, ForeignKey("ship_vias.id"), nullable=True)
    sales_tax_option_id = Column(Integer, ForeignKey("sales_tax_options.id"), nullable=True)
    tax_exempt = Column(Boolean, default=False)
    tax_id_number = Column(String(100), nullable=True)
    internal_memo = Column(Text, nullable=True)
    shipping_memo = Column(Text, nullable=True)
    qb_list_id = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sales_orders = relationship("SalesOrder", back_populates="customer")
    ship_tos = relationship("ShipTo", back_populates="customer", cascade="all, delete-orphan")
    default_ship_via = relationship("ShipVia")
    sales_tax_option = relationship("SalesTaxOption")


class ShipTo(Base):
    __tablename__ = "ship_tos"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="US")
    contact_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    customer = relationship("Customer", back_populates="ship_tos")


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    ship_to_id = Column(Integer, ForeignKey("ship_tos.id"), nullable=True)
    ship_via_id = Column(Integer, ForeignKey("ship_vias.id"), nullable=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    requested_ship_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="draft")  # draft, confirmed, allocated, shipped, invoiced, closed, cancelled
    shipping_method = Column(String(100), nullable=True)
    shipping_address = Column(Text, nullable=True)
    subtotal = Column(Numeric(18, 4), default=0)
    tax_amount = Column(Numeric(18, 4), default=0)
    total_amount = Column(Numeric(18, 4), default=0)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    customer = relationship("Customer", back_populates="sales_orders")
    ship_to = relationship("ShipTo")
    ship_via = relationship("ShipVia")
    lines = relationship("SalesOrderLine", back_populates="sales_order", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="sales_order")
    invoices = relationship("Invoice", back_populates="sales_order")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    id = Column(Integer, primary_key=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    quantity_ordered = Column(Numeric(18, 4), nullable=False)
    quantity_shipped = Column(Numeric(18, 4), default=0)
    unit_price = Column(Numeric(18, 4), nullable=False)
    tax_rate = Column(Numeric(8, 4), default=0)
    line_total = Column(Numeric(18, 4), nullable=False)
    allocated_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    sales_order = relationship("SalesOrder", back_populates="lines")
    item = relationship("Item")
    allocated_lot = relationship("Lot")


class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, index=True)
    shipment_number = Column(String(50), unique=True, nullable=False)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    ship_date = Column(DateTime(timezone=True), server_default=func.now())
    carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(200), nullable=True)
    status = Column(String(30), default="pending")  # pending, shipped, delivered
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sales_order = relationship("SalesOrder", back_populates="shipments")
    lines = relationship("ShipmentLine", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentLine(Base):
    __tablename__ = "shipment_lines"
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    sales_order_line_id = Column(Integer, ForeignKey("sales_order_lines.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity_shipped = Column(Numeric(18, 4), nullable=False)
    shipment = relationship("Shipment", back_populates="lines")
    item = relationship("Item")
    lot = relationship("Lot")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    invoice_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="draft")  # draft, sent, paid, void
    subtotal = Column(Numeric(18, 4), default=0)
    tax_amount = Column(Numeric(18, 4), default=0)
    total_amount = Column(Numeric(18, 4), default=0)
    pdf_path = Column(String(500), nullable=True)
    qb_txn_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sales_order = relationship("SalesOrder", back_populates="invoices")
    customer = relationship("Customer")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    description = Column(String(500), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    line_total = Column(Numeric(18, 4), nullable=False)
    gl_group_id = Column(Integer, ForeignKey("gl_groups.id"), nullable=True)
    invoice = relationship("Invoice", back_populates="lines")
    item = relationship("Item")


class PackingList(Base):
    __tablename__ = "packing_lists"
    id = Column(Integer, primary_key=True, index=True)
    packing_list_number = Column(String(50), unique=True, nullable=False)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    created_date = Column(DateTime(timezone=True), server_default=func.now())
    pdf_path = Column(String(500), nullable=True)
    sales_order = relationship("SalesOrder")
    shipment = relationship("Shipment")
