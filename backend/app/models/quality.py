from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class QCSpecification(Base):
    __tablename__ = "qc_specifications"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    spec_type = Column(String(50), nullable=False)  # incoming, in_process, finished_goods
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    item = relationship("Item")
    tests = relationship("QCTest", back_populates="specification", cascade="all, delete-orphan")


class QCTest(Base):
    __tablename__ = "qc_tests"
    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(Integer, ForeignKey("qc_specifications.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String(200), nullable=False)
    test_method = Column(String(200), nullable=True)
    target_value = Column(Numeric(18, 6), nullable=True)
    min_value = Column(Numeric(18, 6), nullable=True)
    max_value = Column(Numeric(18, 6), nullable=True)
    uom = Column(String(50), nullable=True)
    is_required = Column(Boolean, default=True)
    sequence = Column(Integer, default=0)
    specification = relationship("QCSpecification", back_populates="tests")


class QCResult(Base):
    __tablename__ = "qc_results"
    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    specification_id = Column(Integer, ForeignKey("qc_specifications.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("qc_tests.id"), nullable=False)
    result_value = Column(Numeric(18, 6), nullable=True)
    result_text = Column(String(500), nullable=True)
    passed = Column(Boolean, nullable=True)
    tested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    tested_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    lot = relationship("Lot", back_populates="qc_results")
    specification = relationship("QCSpecification")
    test = relationship("QCTest")
