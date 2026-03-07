from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class QCTestBase(BaseModel):
    test_name: str
    test_method: Optional[str] = None
    target_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    uom: Optional[str] = None
    is_required: bool = True
    sequence: int = 0


class QCTestCreate(QCTestBase):
    pass


class QCTestResponse(QCTestBase):
    id: int
    specification_id: int

    class Config:
        from_attributes = True


class QCSpecBase(BaseModel):
    name: str
    item_id: Optional[int] = None
    spec_type: str  # incoming, in_process, finished_goods


class QCSpecCreate(QCSpecBase):
    tests: List[QCTestCreate] = []


class QCSpecResponse(QCSpecBase):
    id: int
    is_active: bool
    tests: List[QCTestResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class QCResultBase(BaseModel):
    lot_id: int
    specification_id: int
    test_id: int
    result_value: Optional[Decimal] = None
    result_text: Optional[str] = None
    passed: Optional[bool] = None
    notes: Optional[str] = None


class QCResultCreate(QCResultBase):
    pass


class QCResultBatchCreate(BaseModel):
    lot_id: int
    specification_id: int
    results: List[dict]  # [{test_id, result_value, result_text, passed, notes}]


class QCResultResponse(QCResultBase):
    id: int
    tested_by: Optional[int] = None
    tested_at: datetime

    class Config:
        from_attributes = True


class LotDisposition(BaseModel):
    lot_id: int
    action: str  # release, hold, reject
    notes: Optional[str] = None
