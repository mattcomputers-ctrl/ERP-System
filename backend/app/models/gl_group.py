from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GLGroup(Base):
    __tablename__ = "gl_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    account_mappings = relationship("GLAccountMapping", back_populates="gl_group", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="gl_group")


class GLAccountMapping(Base):
    __tablename__ = "gl_account_mappings"
    id = Column(Integer, primary_key=True, index=True)
    gl_group_id = Column(Integer, ForeignKey("gl_groups.id", ondelete="CASCADE"), nullable=False)
    account_type = Column(String(50), nullable=False)  # sales, cogs, inventory_asset, inventory_adjustment
    account_name = Column(String(200), nullable=False)
    account_number = Column(String(50), nullable=True)
    qb_account_ref = Column(String(200), nullable=True)  # QuickBooks account reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    gl_group = relationship("GLGroup", back_populates="account_mappings")
    __table_args__ = (UniqueConstraint("gl_group_id", "account_type", name="uq_gl_group_account_type"),)
