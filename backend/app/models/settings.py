from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ShipVia(Base):
    __tablename__ = "ship_vias"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    carrier = Column(String(100), nullable=True)
    account_number = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Branding(Base):
    __tablename__ = "branding"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False, default="My Company")
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="US")
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    logo_path = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#1e40af")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PriceList(Base):
    __tablename__ = "price_lists"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    price_type = Column(String(20), nullable=False)  # customer, vendor
    entity_id = Column(Integer, nullable=False)  # customer_id or vendor_id
    unit_price = Column(Numeric(18, 4), nullable=False)
    min_quantity = Column(Numeric(18, 4), default=0)
    effective_date = Column(DateTime(timezone=True), server_default=func.now())
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    item = relationship("Item")


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    price_list_id = Column(Integer, ForeignKey("price_lists.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    price_type = Column(String(20), nullable=False)  # customer, vendor
    entity_id = Column(Integer, nullable=False)
    old_price = Column(Numeric(18, 4), nullable=True)
    new_price = Column(Numeric(18, 4), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    item = relationship("Item")
