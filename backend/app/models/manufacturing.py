from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Formula(Base):
    __tablename__ = "formulas"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    product_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    product_item = relationship("Item")
    versions = relationship("FormulaVersion", back_populates="formula", cascade="all, delete-orphan")


class FormulaVersion(Base):
    __tablename__ = "formula_versions"
    id = Column(Integer, primary_key=True, index=True)
    formula_id = Column(Integer, ForeignKey("formulas.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    batch_size = Column(Numeric(18, 4), nullable=False)
    batch_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    expected_yield_percent = Column(Numeric(8, 4), default=100)
    notes = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    formula = relationship("Formula", back_populates="versions")
    batch_uom = relationship("UnitOfMeasure")
    ingredients = relationship("FormulaIngredient", back_populates="formula_version", cascade="all, delete-orphan")


class FormulaIngredient(Base):
    __tablename__ = "formula_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    formula_version_id = Column(Integer, ForeignKey("formula_versions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    quantity = Column(Numeric(18, 6), nullable=False)
    uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    percentage = Column(Numeric(8, 4), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    formula_version = relationship("FormulaVersion", back_populates="ingredients")
    item = relationship("Item")
    uom = relationship("UnitOfMeasure")


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    formula_id = Column(Integer, ForeignKey("formulas.id"), nullable=False)
    formula_version_id = Column(Integer, ForeignKey("formula_versions.id"), nullable=False)
    planned_quantity = Column(Numeric(18, 4), nullable=False)
    actual_quantity = Column(Numeric(18, 4), nullable=True)
    planned_start_date = Column(DateTime(timezone=True), nullable=True)
    actual_start_date = Column(DateTime(timezone=True), nullable=True)
    planned_end_date = Column(DateTime(timezone=True), nullable=True)
    actual_end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="planned")  # planned, released, in_production, qc_hold, completed, rejected
    output_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    output_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    output_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    yield_percent = Column(Numeric(8, 4), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    formula = relationship("Formula")
    formula_version = relationship("FormulaVersion")
    output_lot = relationship("Lot")
    consumptions = relationship("ProductionConsumption", back_populates="production_order", cascade="all, delete-orphan")
    outputs = relationship("ProductionOutput", back_populates="production_order", cascade="all, delete-orphan")


class ProductionConsumption(Base):
    __tablename__ = "production_consumptions"
    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    planned_quantity = Column(Numeric(18, 4), nullable=False)
    actual_quantity = Column(Numeric(18, 4), nullable=True)
    unit_cost = Column(Numeric(18, 6), nullable=True)
    total_cost = Column(Numeric(18, 4), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    production_order = relationship("ProductionOrder", back_populates="consumptions")
    item = relationship("Item")
    lot = relationship("Lot")


class ProductionOutput(Base):
    __tablename__ = "production_outputs"
    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 6), nullable=True)
    total_cost = Column(Numeric(18, 4), nullable=True)
    produced_at = Column(DateTime(timezone=True), server_default=func.now())
    production_order = relationship("ProductionOrder", back_populates="outputs")
    item = relationship("Item")
    lot = relationship("Lot")
