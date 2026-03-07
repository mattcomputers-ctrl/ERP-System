from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.gl_group import GLGroup, GLAccountMapping
from app.schemas.gl_group import GLGroupCreate, GLGroupUpdate, GLGroupResponse, GLAccountMappingBase

router = APIRouter(prefix="/gl-groups", tags=["GL Groups"])


@router.get("", response_model=List[GLGroupResponse])
def list_gl_groups(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(GLGroup).all()


@router.post("", response_model=GLGroupResponse, status_code=status.HTTP_201_CREATED)
def create_gl_group(
    gl_in: GLGroupCreate,
    current_user=Depends(require_permission("admin", "create")),
    db: Session = Depends(get_db),
):
    gl_group = GLGroup(name=gl_in.name, description=gl_in.description)
    db.add(gl_group)
    db.flush()
    for mapping in gl_in.account_mappings:
        am = GLAccountMapping(gl_group_id=gl_group.id, **mapping.model_dump())
        db.add(am)
    db.commit()
    db.refresh(gl_group)
    return gl_group


@router.get("/{gl_group_id}", response_model=GLGroupResponse)
def get_gl_group(gl_group_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    gl_group = db.query(GLGroup).filter(GLGroup.id == gl_group_id).first()
    if not gl_group:
        raise HTTPException(status_code=404, detail="GL Group not found")
    return gl_group


@router.put("/{gl_group_id}", response_model=GLGroupResponse)
def update_gl_group(
    gl_group_id: int, gl_in: GLGroupUpdate,
    current_user=Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    gl_group = db.query(GLGroup).filter(GLGroup.id == gl_group_id).first()
    if not gl_group:
        raise HTTPException(status_code=404, detail="GL Group not found")
    for key, value in gl_in.model_dump(exclude_unset=True).items():
        setattr(gl_group, key, value)
    db.commit()
    db.refresh(gl_group)
    return gl_group


@router.put("/{gl_group_id}/mappings")
def set_account_mappings(
    gl_group_id: int, mappings: List[GLAccountMappingBase],
    current_user=Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    db.query(GLAccountMapping).filter(GLAccountMapping.gl_group_id == gl_group_id).delete()
    for m in mappings:
        am = GLAccountMapping(gl_group_id=gl_group_id, **m.model_dump())
        db.add(am)
    db.commit()
    return {"detail": "Account mappings updated"}
