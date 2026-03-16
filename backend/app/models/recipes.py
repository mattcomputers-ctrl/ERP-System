from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Recipe(Base):
    """A recipe links to a product item. Versions are numbered as ItemCode.01, .02, etc."""
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    product_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    product_item = relationship("Item", foreign_keys=[product_item_id])
    versions = relationship("RecipeVersion", back_populates="recipe", cascade="all, delete-orphan",
                            order_by="RecipeVersion.version_number.desc()")


class RecipeVersion(Base):
    """Each version of a recipe. Recipe number = ItemCode.XX (zero-padded version_number)."""
    __tablename__ = "recipe_versions"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(String(30), default="draft")  # draft, published
    comment = Column(Text, nullable=True)  # reason for this version
    batch_size = Column(Numeric(18, 4), nullable=True)
    batch_uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    expected_yield_percent = Column(Numeric(8, 4), default=100)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    recipe = relationship("Recipe", back_populates="versions")
    batch_uom = relationship("UnitOfMeasure")
    ingredients = relationship("RecipeIngredient", back_populates="recipe_version",
                               cascade="all, delete-orphan", order_by="RecipeIngredient.sequence")
    procedure_steps = relationship("RecipeProcedureStep", back_populates="recipe_version",
                                    cascade="all, delete-orphan", order_by="RecipeProcedureStep.sequence")


class RecipeIngredient(Base):
    """Ingredients entered as weight percent."""
    __tablename__ = "recipe_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    recipe_version_id = Column(Integer, ForeignKey("recipe_versions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    weight_percent = Column(Numeric(8, 4), nullable=False)
    notes = Column(Text, nullable=True)
    recipe_version = relationship("RecipeVersion", back_populates="ingredients")
    item = relationship("Item")


class RecipeProcedureStep(Base):
    """Ordered procedure steps: either 'add_formula' (adds all ingredients) or 'instruction' (free text)."""
    __tablename__ = "recipe_procedure_steps"
    id = Column(Integer, primary_key=True, index=True)
    recipe_version_id = Column(Integer, ForeignKey("recipe_versions.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    step_type = Column(String(30), nullable=False)  # add_formula, instruction
    instruction_text = Column(Text, nullable=True)
    recipe_version = relationship("RecipeVersion", back_populates="procedure_steps")


class BatchTicket(Base):
    """Planning ticket for batch production or repack. No inventory movement until execution."""
    __tablename__ = "batch_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    ticket_type = Column(String(20), nullable=False)  # batch, repack
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    recipe_version_id = Column(Integer, ForeignKey("recipe_versions.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_quantity = Column(Numeric(18, 4), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(String(30), default="draft")  # draft, planned, in_progress, completed, cancelled
    has_shortage = Column(Boolean, default=False)
    shortage_override = Column(Boolean, default=False)
    shortage_details = Column(Text, nullable=True)  # JSON of shortage items
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    recipe = relationship("Recipe")
    recipe_version = relationship("RecipeVersion")
    item = relationship("Item")
    customer = relationship("Customer")
    packages = relationship("BatchTicketPackage", back_populates="batch_ticket", cascade="all, delete-orphan")
    planned_materials = relationship("BatchTicketMaterial", back_populates="batch_ticket", cascade="all, delete-orphan")
    execution = relationship("BatchExecution", back_populates="batch_ticket", uselist=False)


class BatchTicketPackage(Base):
    """Which pack extensions and quantities are planned for a batch ticket."""
    __tablename__ = "batch_ticket_packages"
    id = Column(Integer, primary_key=True, index=True)
    batch_ticket_id = Column(Integer, ForeignKey("batch_tickets.id", ondelete="CASCADE"), nullable=False)
    pack_extension_id = Column(Integer, ForeignKey("pack_extension_definitions.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    batch_ticket = relationship("BatchTicket", back_populates="packages")
    pack_extension = relationship("PackExtensionDefinition")


class BatchTicketMaterial(Base):
    """Planned material requirements calculated from recipe for a batch ticket."""
    __tablename__ = "batch_ticket_materials"
    id = Column(Integer, primary_key=True, index=True)
    batch_ticket_id = Column(Integer, ForeignKey("batch_tickets.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_quantity = Column(Numeric(18, 4), nullable=False)
    available_quantity = Column(Numeric(18, 4), nullable=True)
    has_shortage = Column(Boolean, default=False)
    batch_ticket = relationship("BatchTicket", back_populates="planned_materials")
    item = relationship("Item")


class BatchExecution(Base):
    """Execution record for a batch/repack ticket. This is where inventory actually moves."""
    __tablename__ = "batch_executions"
    id = Column(Integer, primary_key=True, index=True)
    batch_ticket_id = Column(Integer, ForeignKey("batch_tickets.id"), unique=True, nullable=False)
    status = Column(String(30), default="in_progress")  # in_progress, completed
    actual_yield = Column(Numeric(18, 4), nullable=True)
    yield_percent = Column(Numeric(8, 4), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    batch_ticket = relationship("BatchTicket", back_populates="execution")
    consumptions = relationship("BatchExecutionConsumption", back_populates="execution", cascade="all, delete-orphan")
    outputs = relationship("BatchExecutionOutput", back_populates="execution", cascade="all, delete-orphan")


class BatchExecutionConsumption(Base):
    """Actual materials consumed during batch execution."""
    __tablename__ = "batch_execution_consumptions"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("batch_executions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    planned_quantity = Column(Numeric(18, 4), nullable=True)
    actual_quantity = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 6), nullable=True)
    total_cost = Column(Numeric(18, 4), nullable=True)
    execution = relationship("BatchExecution", back_populates="consumptions")
    item = relationship("Item")
    lot = relationship("Lot")


class BatchExecutionOutput(Base):
    """Output produced during batch execution."""
    __tablename__ = "batch_execution_outputs"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("batch_executions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 6), nullable=True)
    total_cost = Column(Numeric(18, 4), nullable=True)
    execution = relationship("BatchExecution", back_populates="outputs")
    item = relationship("Item")
    lot = relationship("Lot")
