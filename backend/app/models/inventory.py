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
    # General tab fields
    tracking_type = Column(String(50), default="inventory_lot")  # inventory_lot, inventory_no_lot, not_inventoried
    max_shelf_life_days = Column(Integer, nullable=True)
    does_not_expire = Column(Boolean, default=False)
    target_min_qty = Column(Numeric(18, 4), nullable=True)
    master_recipe_id = Column(Integer, ForeignKey("formulas.id"), nullable=True)
    current_fifo_cost = Column(Numeric(18, 6), nullable=True)
    replacement_cost = Column(Numeric(18, 6), nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    preferred_supplier_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    # Technical/Safety tab fields
    specific_gravity = Column(Numeric(12, 6), nullable=True)
    density_lb_gal = Column(Numeric(12, 6), nullable=True)
    voc_percent = Column(Numeric(8, 4), nullable=True)
    boiling_point = Column(String(100), nullable=True)
    flash_point = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    gl_group = relationship("GLGroup", back_populates="items")
    primary_uom = relationship("UnitOfMeasure")
    master_recipe = relationship("Formula", foreign_keys=[master_recipe_id])
    preferred_supplier = relationship("Vendor", foreign_keys=[preferred_supplier_id])
    lots = relationship("Lot", back_populates="item")
    aliases = relationship("ItemAlias", back_populates="item", cascade="all, delete-orphan")
    pack_components = relationship("PackComponent", back_populates="pack_item", foreign_keys="PackComponent.pack_item_id", cascade="all, delete-orphan")
    active_recipes = relationship("ItemActiveRecipe", back_populates="item", cascade="all, delete-orphan")
    qc_test_assignments = relationship("ItemQCTest", back_populates="item", cascade="all, delete-orphan")
    item_pack_extensions = relationship("ItemPackExtension", back_populates="item", cascade="all, delete-orphan")


class ItemAlias(Base):
    """Alternate product codes/descriptions that point to an item.
    Allows internal and external codes (e.g., customer part numbers, supplier codes)."""
    __tablename__ = "item_aliases"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    alias_code = Column(String(100), nullable=False, index=True)
    alias_name = Column(String(255), nullable=True)
    alias_type = Column(String(50), nullable=True)  # customer, vendor, internal, regulatory, legacy
    reference_id = Column(Integer, nullable=True)  # optional: customer_id or vendor_id for context
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    item = relationship("Item", back_populates="aliases")
    __table_args__ = (UniqueConstraint("alias_code", "alias_type", name="uq_alias_code_type"),)


class PackComponent(Base):
    """Defines what items and quantities make up a pack/bundle.
    The pack_item_id is the packed item; component_item_id is a contained item."""
    __tablename__ = "pack_components"
    id = Column(Integer, primary_key=True, index=True)
    pack_item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    component_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    sequence = Column(Integer, default=0)
    uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    pack_item = relationship("Item", back_populates="pack_components", foreign_keys=[pack_item_id])
    component_item = relationship("Item", foreign_keys=[component_item_id])
    uom = relationship("UnitOfMeasure")
    __table_args__ = (UniqueConstraint("pack_item_id", "component_item_id", name="uq_pack_component"),)


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
    pack_extension_id = Column(Integer, ForeignKey("pack_extension_definitions.id"), nullable=True)
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
    pack_extension = relationship("PackExtensionDefinition")
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


class ItemActiveRecipe(Base):
    """Links active recipes (formulas) to an item. Multiple recipes can be active."""
    __tablename__ = "item_active_recipes"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    formula_id = Column(Integer, ForeignKey("formulas.id"), nullable=False)
    is_master = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = relationship("Item", back_populates="active_recipes")
    formula = relationship("Formula")
    __table_args__ = (UniqueConstraint("item_id", "formula_id", name="uq_item_active_recipe"),)


class QCTestDefinition(Base):
    """Global QC test definitions configured in settings. Either pass/fail or range-based."""
    __tablename__ = "qc_test_definitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    test_type = Column(String(20), nullable=False)  # pass_fail, range
    method = Column(String(200), nullable=True)
    uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    uom = relationship("UnitOfMeasure")


class ItemQCTest(Base):
    """Assignment of a QC test definition to an item with target specs."""
    __tablename__ = "item_qc_tests"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    qc_test_definition_id = Column(Integer, ForeignKey("qc_test_definitions.id"), nullable=False)
    target_value = Column(Numeric(18, 6), nullable=True)
    min_value = Column(Numeric(18, 6), nullable=True)
    max_value = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = relationship("Item", back_populates="qc_test_assignments")
    qc_test_definition = relationship("QCTestDefinition")
    __table_args__ = (UniqueConstraint("item_id", "qc_test_definition_id", name="uq_item_qc_test"),)


class PackExtensionDefinition(Base):
    """Pack extension definitions configured in settings (e.g., '-50' = 5LB can)."""
    __tablename__ = "pack_extension_definitions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    materials = relationship("PackExtensionMaterial", back_populates="pack_extension", cascade="all, delete-orphan")


class PackExtensionMaterial(Base):
    """Packaging materials consumed per pound of product for a pack extension."""
    __tablename__ = "pack_extension_materials"
    id = Column(Integer, primary_key=True, index=True)
    pack_extension_id = Column(Integer, ForeignKey("pack_extension_definitions.id", ondelete="CASCADE"), nullable=False)
    material_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_per_lb = Column(Numeric(18, 6), nullable=False)  # e.g., 0.2 ea per 1 lb
    uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    pack_extension = relationship("PackExtensionDefinition", back_populates="materials")
    material_item = relationship("Item")
    uom = relationship("UnitOfMeasure")
    __table_args__ = (UniqueConstraint("pack_extension_id", "material_item_id", name="uq_pack_ext_material"),)


class ItemPackExtension(Base):
    """Assignment of a pack extension to an item with desired fill amount."""
    __tablename__ = "item_pack_extensions"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    pack_extension_id = Column(Integer, ForeignKey("pack_extension_definitions.id"), nullable=False)
    desired_fill_amount = Column(Numeric(18, 4), nullable=True)
    fill_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = relationship("Item", back_populates="item_pack_extensions")
    pack_extension = relationship("PackExtensionDefinition")
    fill_uom = relationship("UnitOfMeasure")
    __table_args__ = (UniqueConstraint("item_id", "pack_extension_id", name="uq_item_pack_extension"),)
