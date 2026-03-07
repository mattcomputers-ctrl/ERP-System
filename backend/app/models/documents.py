from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentTemplate(Base):
    """User-configurable document templates for the drag-and-drop builder."""
    __tablename__ = "document_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    doc_type = Column(String(50), nullable=False)  # invoice, purchase_order, packing_list, batch_ticket, coa, custom
    description = Column(Text, nullable=True)
    # JSON-encoded layout definition: sections, fields, positions, styles
    layout_json = Column(Text, nullable=False, default="{}")
    # Optional header/footer HTML or text
    header_html = Column(Text, nullable=True)
    footer_html = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeneratedDocument(Base):
    """Record of generated PDFs for audit trail."""
    __tablename__ = "generated_documents"
    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String(50), nullable=False)
    reference_type = Column(String(50), nullable=False)  # invoice, purchase_order, packing_list, production_order, lot
    reference_id = Column(Integer, nullable=False)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    template = relationship("DocumentTemplate")


class COACertificate(Base):
    """Certificate of Analysis linked to a lot and its QC results."""
    __tablename__ = "coa_certificates"
    id = Column(Integer, primary_key=True, index=True)
    certificate_number = Column(String(50), unique=True, nullable=False, index=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    specification_id = Column(Integer, ForeignKey("qc_specifications.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    status = Column(String(30), default="draft")  # draft, approved, sent
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lot = relationship("Lot")
    specification = relationship("QCSpecification")
    customer = relationship("Customer")
