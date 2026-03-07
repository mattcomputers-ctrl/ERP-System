from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentTemplateBase(BaseModel):
    name: str
    doc_type: str
    description: Optional[str] = None
    layout_json: str = "{}"
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    is_default: bool = False


class DocumentTemplateCreate(DocumentTemplateBase):
    pass


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout_json: Optional[str] = None
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class DocumentTemplateResponse(DocumentTemplateBase):
    id: int
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateDocumentRequest(BaseModel):
    doc_type: str  # invoice, purchase_order, packing_list, batch_ticket, coa
    reference_id: int
    template_id: Optional[int] = None


class GeneratedDocumentResponse(BaseModel):
    id: int
    doc_type: str
    reference_type: str
    reference_id: int
    template_id: Optional[int] = None
    file_path: str
    file_name: str
    generated_by: Optional[int] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class COACreateRequest(BaseModel):
    lot_id: int
    specification_id: Optional[int] = None
    customer_id: Optional[int] = None
    notes: Optional[str] = None


class COAApproveRequest(BaseModel):
    notes: Optional[str] = None


class COAResponse(BaseModel):
    id: int
    certificate_number: str
    lot_id: int
    specification_id: Optional[int] = None
    customer_id: Optional[int] = None
    pdf_path: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
