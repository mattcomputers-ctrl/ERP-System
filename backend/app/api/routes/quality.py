from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.quality import QCSpecification, QCTest, QCResult
from app.models.inventory import Lot
from app.schemas.quality import (
    QCSpecCreate, QCSpecResponse,
    QCResultCreate, QCResultBatchCreate, QCResultResponse,
    LotDisposition,
)

router = APIRouter(prefix="/quality", tags=["Quality Control"])


# --- QC Specifications ---

@router.get("/specifications", response_model=List[QCSpecResponse])
def list_specifications(
    item_id: Optional[int] = None, spec_type: Optional[str] = None,
    current_user=Depends(require_permission("quality", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(QCSpecification).filter(QCSpecification.is_active == True)
    if item_id:
        q = q.filter(QCSpecification.item_id == item_id)
    if spec_type:
        q = q.filter(QCSpecification.spec_type == spec_type)
    return q.all()


@router.post("/specifications", response_model=QCSpecResponse, status_code=status.HTTP_201_CREATED)
def create_specification(
    spec_in: QCSpecCreate,
    current_user=Depends(require_permission("quality", "create")),
    db: Session = Depends(get_db),
):
    spec = QCSpecification(name=spec_in.name, item_id=spec_in.item_id, spec_type=spec_in.spec_type)
    for t in spec_in.tests:
        test = QCTest(**t.model_dump())
        spec.tests.append(test)
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


@router.get("/specifications/{spec_id}", response_model=QCSpecResponse)
def get_specification(spec_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    spec = db.query(QCSpecification).filter(QCSpecification.id == spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    return spec


# --- QC Results ---

@router.get("/results", response_model=List[QCResultResponse])
def list_results(
    lot_id: Optional[int] = None,
    current_user=Depends(require_permission("quality", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(QCResult)
    if lot_id:
        q = q.filter(QCResult.lot_id == lot_id)
    return q.all()


@router.post("/results", response_model=QCResultResponse, status_code=status.HTTP_201_CREATED)
def record_result(
    result_in: QCResultCreate,
    current_user=Depends(require_permission("quality", "create")),
    db: Session = Depends(get_db),
):
    result = QCResult(**result_in.model_dump(), tested_by=current_user.id)
    # Auto-determine pass/fail if min/max defined
    test = db.query(QCTest).filter(QCTest.id == result_in.test_id).first()
    if test and result_in.result_value is not None:
        if test.min_value is not None and test.max_value is not None:
            result.passed = test.min_value <= result_in.result_value <= test.max_value
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.post("/results/batch")
def record_batch_results(
    batch_in: QCResultBatchCreate,
    current_user=Depends(require_permission("quality", "create")),
    db: Session = Depends(get_db),
):
    created = []
    for r in batch_in.results:
        test = db.query(QCTest).filter(QCTest.id == r["test_id"]).first()
        result = QCResult(
            lot_id=batch_in.lot_id,
            specification_id=batch_in.specification_id,
            test_id=r["test_id"],
            result_value=r.get("result_value"),
            result_text=r.get("result_text"),
            passed=r.get("passed"),
            notes=r.get("notes"),
            tested_by=current_user.id,
        )
        if test and result.result_value is not None and result.passed is None:
            if test.min_value is not None and test.max_value is not None:
                result.passed = test.min_value <= result.result_value <= test.max_value
        db.add(result)
        created.append(result)
    db.commit()
    return {"detail": f"{len(created)} results recorded"}


# --- Lot Disposition ---

@router.post("/lot-disposition")
def set_lot_disposition(
    disp: LotDisposition,
    current_user=Depends(require_permission("quality", "approve")),
    db: Session = Depends(get_db),
):
    lot = db.query(Lot).filter(Lot.id == disp.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    if disp.action == "release":
        lot.status = "available"
        if lot.quantity_on_hold > 0:
            lot.quantity_on_hand += lot.quantity_on_hold
            lot.quantity_on_hold = 0
    elif disp.action == "hold":
        lot.status = "on_hold"
    elif disp.action == "reject":
        lot.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    db.commit()
    return {"detail": f"Lot {lot.lot_number} status set to {lot.status}"}
