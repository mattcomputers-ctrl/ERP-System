from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    abbreviation = Column(String(10), unique=True, nullable=False)
    category = Column(String(50), nullable=False)  # weight, volume, count, length


class UOMConversion(Base):
    __tablename__ = "uom_conversions"
    id = Column(Integer, primary_key=True, index=True)
    from_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=False)
    to_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=False)
    factor = Column(Numeric(18, 8), nullable=False)
    from_uom = relationship("UnitOfMeasure", foreign_keys=[from_uom_id])
    to_uom = relationship("UnitOfMeasure", foreign_keys=[to_uom_id])
    __table_args__ = (UniqueConstraint("from_uom_id", "to_uom_id", name="uq_uom_conversion"),)


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    item_type = Column(String(50), nullable=False)  # raw_material, finished_good, packaging, intermediate, consumable
    gl_group_id = Column(Integer, ForeignKey("gl_groups.id"), nullable=True)
    primary_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    reorder_level = Column(Numeric(18, 4), nullable=True)
    safety_stock = Column(Numeric(18, 4), nullable=True)
    is_lot_tracked = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    gl_group = relationship("GLGroup", back_populates="items")
    primary_uom = relationship("UnitOfMeasure")
    lots = relationship("Lot", back_populates="item")


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    locations = relationship("Location", back_populates="warehouse")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    warehouse = relationship("Warehouse", back_populates="locations")
    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uq_warehouse_location"),)


class Lot(Base):
    __tablename__ = "lots"
    id = Column(Integer, primary_key=True, index=True)
    lot_number = Column(String(100), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    quantity_on_hand = Column(Numeric(18, 4), default=0)
    quantity_allocated = Column(Numeric(18, 4), default=0)
    quantity_on_hold = Column(Numeric(18, 4), default=0)
    status = Column(String(30), default="available")  # available, on_hold, rejected, expired
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    vendor_lot_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = relationship("Item", back_populates="lots")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
    qc_results = relationship("QCResult", back_populates="lot")


class FIFOCostLayer(Base):
    __tablename__ = "fifo_cost_layers"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity_remaining = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 6), nullable=False)
    total_cost = Column(Numeric(18, 4), nullable=False)
    received_date = Column(DateTime(timezone=True), server_default=func.now())
    reference_type = Column(String(50), nullable=True)  # purchase_receipt, production_output, adjustment
    reference_id = Column(Integer, nullable=True)
    item = relationship("Item")
    lot = relationship("Lot")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(50), nullable=False)  # receipt, consumption, output, adjustment, transfer, shipment
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 6), nullable=True)
    total_cost = Column(Numeric(18, 4), nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(Integer, nullable=True)
    gl_group_id = Column(Integer, ForeignKey("gl_groups.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = relationship("Item")
    lot = relationship("Lot")
    gl_group = relationship("GLGroup")
