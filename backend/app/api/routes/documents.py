"""
Document generation and template management routes.
Handles PDF generation for invoices, POs, packing lists, batch tickets, and COAs.
Also manages the document template builder.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import os

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.documents import DocumentTemplate, GeneratedDocument, COACertificate
from app.models.sales import Invoice, Customer, PackingList, SalesOrder, Shipment, ShipmentLine
from app.models.purchasing import PurchaseOrder, Vendor
from app.models.manufacturing import ProductionOrder, Formula, FormulaVersion, FormulaIngredient
from app.models.inventory import Lot, Item
from app.models.quality import QCSpecification, QCResult
from app.models.settings import Branding
from app.schemas.documents import (
    DocumentTemplateCreate, DocumentTemplateUpdate, DocumentTemplateResponse,
    GenerateDocumentRequest, GeneratedDocumentResponse,
    COACreateRequest, COAApproveRequest, COAResponse,
)
from app.services.pdf_generator import (
    generate_invoice_pdf, generate_purchase_order_pdf,
    generate_packing_list_pdf, generate_batch_ticket_pdf, generate_coa_pdf,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


def _get_branding(db: Session):
    branding = db.query(Branding).first()
    if not branding:
        branding = Branding(company_name="My Company")
        db.add(branding)
        db.commit()
        db.refresh(branding)
    return branding


def _next_coa_number(db: Session) -> str:
    last = db.query(COACertificate).order_by(COACertificate.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"COA-{num:06d}"


# ============================================================
# Document Templates (Drag-and-Drop Builder)
# ============================================================

@router.get("/templates", response_model=List[DocumentTemplateResponse])
def list_templates(
    doc_type: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DocumentTemplate).filter(DocumentTemplate.is_active == True)
    if doc_type:
        q = q.filter(DocumentTemplate.doc_type == doc_type)
    return q.order_by(DocumentTemplate.name).all()


@router.get("/templates/{template_id}", response_model=DocumentTemplateResponse)
def get_template(template_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post("/templates", response_model=DocumentTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    t_in: DocumentTemplateCreate,
    current_user=Depends(require_permission("documents", "create")),
    db: Session = Depends(get_db),
):
    # If setting as default, unset other defaults for same doc_type
    if t_in.is_default:
        db.query(DocumentTemplate).filter(
            DocumentTemplate.doc_type == t_in.doc_type,
            DocumentTemplate.is_default == True,
        ).update({"is_default": False})
    t = DocumentTemplate(**t_in.model_dump(), created_by=current_user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/templates/{template_id}", response_model=DocumentTemplateResponse)
def update_template(
    template_id: int,
    t_in: DocumentTemplateUpdate,
    current_user=Depends(require_permission("documents", "update")),
    db: Session = Depends(get_db),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    update_data = t_in.model_dump(exclude_unset=True)
    if update_data.get("is_default"):
        db.query(DocumentTemplate).filter(
            DocumentTemplate.doc_type == t.doc_type,
            DocumentTemplate.is_default == True,
            DocumentTemplate.id != template_id,
        ).update({"is_default": False})
    for k, v in update_data.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    current_user=Depends(require_permission("documents", "delete")),
    db: Session = Depends(get_db),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    t.is_active = False
    db.commit()
    return {"detail": "Template deactivated"}


# ============================================================
# PDF Generation
# ============================================================

@router.post("/generate", response_model=GeneratedDocumentResponse)
def generate_document(
    req: GenerateDocumentRequest,
    current_user=Depends(require_permission("documents", "create")),
    db: Session = Depends(get_db),
):
    branding = _get_branding(db)
    file_path = ""
    file_name = ""
    reference_type = req.doc_type

    if req.doc_type == "invoice":
        invoice = db.query(Invoice).filter(Invoice.id == req.reference_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()
        file_path = generate_invoice_pdf(invoice, customer, branding)
        file_name = os.path.basename(file_path)
        invoice.pdf_path = file_path
        reference_type = "invoice"

    elif req.doc_type == "purchase_order":
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == req.reference_id).first()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        vendor = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()
        file_path = generate_purchase_order_pdf(po, vendor, branding)
        file_name = os.path.basename(file_path)
        po.pdf_path = file_path
        reference_type = "purchase_order"

    elif req.doc_type == "packing_list":
        so = db.query(SalesOrder).filter(SalesOrder.id == req.reference_id).first()
        if not so:
            raise HTTPException(status_code=404, detail="Sales order not found")
        customer = db.query(Customer).filter(Customer.id == so.customer_id).first()
        # Find or create packing list
        pl = db.query(PackingList).filter(PackingList.sales_order_id == so.id).first()
        if not pl:
            pl_num = f"PL-{so.order_number}"
            pl = PackingList(packing_list_number=pl_num, sales_order_id=so.id)
            db.add(pl)
            db.flush()
        shipment = db.query(Shipment).filter(Shipment.sales_order_id == so.id).order_by(Shipment.id.desc()).first()
        shipment_lines = []
        if shipment:
            shipment_lines = db.query(ShipmentLine).filter(ShipmentLine.shipment_id == shipment.id).all()
            pl.shipment_id = shipment.id
        file_path = generate_packing_list_pdf(pl, so, customer, shipment, shipment_lines, branding)
        file_name = os.path.basename(file_path)
        pl.pdf_path = file_path
        reference_type = "packing_list"

    elif req.doc_type == "batch_ticket":
        po_order = db.query(ProductionOrder).filter(ProductionOrder.id == req.reference_id).first()
        if not po_order:
            raise HTTPException(status_code=404, detail="Production order not found")
        formula = db.query(Formula).filter(Formula.id == po_order.formula_id).first()
        fv = db.query(FormulaVersion).filter(FormulaVersion.id == po_order.formula_version_id).first()
        ingredients = db.query(FormulaIngredient).filter(
            FormulaIngredient.formula_version_id == fv.id,
            FormulaIngredient.is_active == True
        ).order_by(FormulaIngredient.sequence).all() if fv else []
        file_path = generate_batch_ticket_pdf(po_order, formula, fv, ingredients, branding)
        file_name = os.path.basename(file_path)
        reference_type = "production_order"

    elif req.doc_type == "coa":
        lot = db.query(Lot).filter(Lot.id == req.reference_id).first()
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        item = db.query(Item).filter(Item.id == lot.item_id).first()
        qc_results = db.query(QCResult).filter(QCResult.lot_id == lot.id).all()
        spec = None
        if qc_results:
            spec = db.query(QCSpecification).filter(QCSpecification.id == qc_results[0].specification_id).first()
        file_path = generate_coa_pdf(lot, item, spec, qc_results, branding)
        file_name = os.path.basename(file_path)
        reference_type = "lot"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported document type: {req.doc_type}")

    # Record the generated document
    doc = GeneratedDocument(
        doc_type=req.doc_type,
        reference_type=reference_type,
        reference_id=req.reference_id,
        template_id=req.template_id,
        file_path=file_path,
        file_name=file_name,
        generated_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/generated", response_model=List[GeneratedDocumentResponse])
def list_generated_documents(
    doc_type: Optional[str] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    skip: int = 0, limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(GeneratedDocument)
    if doc_type:
        q = q.filter(GeneratedDocument.doc_type == doc_type)
    if reference_type:
        q = q.filter(GeneratedDocument.reference_type == reference_type)
    if reference_id:
        q = q.filter(GeneratedDocument.reference_id == reference_id)
    return q.order_by(GeneratedDocument.generated_at.desc()).offset(skip).limit(limit).all()


@router.get("/download/{doc_id}")
def download_document(doc_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(doc.file_path, filename=doc.file_name, media_type="application/pdf")


# ============================================================
# Certificate of Analysis (COA)
# ============================================================

@router.get("/coa", response_model=List[COAResponse])
def list_coas(
    lot_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(COACertificate)
    if lot_id:
        q = q.filter(COACertificate.lot_id == lot_id)
    if status:
        q = q.filter(COACertificate.status == status)
    return q.order_by(COACertificate.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/coa/{coa_id}", response_model=COAResponse)
def get_coa(coa_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    coa = db.query(COACertificate).filter(COACertificate.id == coa_id).first()
    if not coa:
        raise HTTPException(status_code=404, detail="COA not found")
    return coa


@router.post("/coa", response_model=COAResponse, status_code=status.HTTP_201_CREATED)
def create_coa(
    req: COACreateRequest,
    current_user=Depends(require_permission("quality", "create")),
    db: Session = Depends(get_db),
):
    lot = db.query(Lot).filter(Lot.id == req.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    # Generate the COA PDF
    branding = _get_branding(db)
    item = db.query(Item).filter(Item.id == lot.item_id).first()
    customer = db.query(Customer).filter(Customer.id == req.customer_id).first() if req.customer_id else None

    qc_filter = QCResult.lot_id == lot.id
    if req.specification_id:
        qc_results = db.query(QCResult).filter(qc_filter, QCResult.specification_id == req.specification_id).all()
        spec = db.query(QCSpecification).filter(QCSpecification.id == req.specification_id).first()
    else:
        qc_results = db.query(QCResult).filter(qc_filter).all()
        spec = db.query(QCSpecification).filter(QCSpecification.id == qc_results[0].specification_id).first() if qc_results else None

    pdf_path = generate_coa_pdf(lot, item, spec, qc_results, branding, customer)

    coa = COACertificate(
        certificate_number=_next_coa_number(db),
        lot_id=req.lot_id,
        specification_id=req.specification_id,
        customer_id=req.customer_id,
        pdf_path=pdf_path,
        notes=req.notes,
        created_by=current_user.id,
    )
    db.add(coa)
    db.commit()
    db.refresh(coa)
    return coa


@router.post("/coa/{coa_id}/approve", response_model=COAResponse)
def approve_coa(
    coa_id: int,
    req: COAApproveRequest,
    current_user=Depends(require_permission("quality", "approve")),
    db: Session = Depends(get_db),
):
    coa = db.query(COACertificate).filter(COACertificate.id == coa_id).first()
    if not coa:
        raise HTTPException(status_code=404, detail="COA not found")
    if coa.status == "approved":
        raise HTTPException(status_code=400, detail="COA is already approved")
    coa.status = "approved"
    coa.approved_by = current_user.id
    coa.approved_at = datetime.now(timezone.utc)
    if req.notes:
        coa.notes = req.notes
    db.commit()
    db.refresh(coa)
    return coa


@router.get("/coa/{coa_id}/download")
def download_coa(coa_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    coa = db.query(COACertificate).filter(COACertificate.id == coa_id).first()
    if not coa:
        raise HTTPException(status_code=404, detail="COA not found")
    if not coa.pdf_path or not os.path.exists(coa.pdf_path):
        raise HTTPException(status_code=404, detail="COA PDF not found on disk")
    return FileResponse(coa.pdf_path, filename=f"COA_{coa.certificate_number}.pdf", media_type="application/pdf")
