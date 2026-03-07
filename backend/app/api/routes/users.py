from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import hash_password, get_current_user, require_permission
from app.models.user import User, UserGroup, UserGroupAssociation, GroupPermission
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    UserGroupCreate, UserGroupResponse,
    GroupPermissionSet, GroupPermissionResponse, PermissionBase,
)

router = APIRouter(prefix="/users", tags=["Users & Permissions"])


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(require_permission("admin", "read")),
    db: Session = Depends(get_db),
):
    return db.query(User).offset(skip).limit(limit).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_permission("admin", "create")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int, user_in: UserUpdate,
    current_user: User = Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


# --- User Groups ---

@router.get("/groups/", response_model=List[UserGroupResponse])
def list_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UserGroup).all()


@router.post("/groups/", response_model=UserGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_in: UserGroupCreate,
    current_user: User = Depends(require_permission("admin", "create")),
    db: Session = Depends(get_db),
):
    group = UserGroup(**group_in.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.post("/groups/{group_id}/users/{user_id}")
def add_user_to_group(
    group_id: int, user_id: int,
    current_user: User = Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    assoc = UserGroupAssociation(user_id=user_id, group_id=group_id, assigned_by=current_user.id)
    db.add(assoc)
    db.commit()
    return {"detail": "User added to group"}


@router.delete("/groups/{group_id}/users/{user_id}")
def remove_user_from_group(
    group_id: int, user_id: int,
    current_user: User = Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    assoc = db.query(UserGroupAssociation).filter_by(user_id=user_id, group_id=group_id).first()
    if assoc:
        db.delete(assoc)
        db.commit()
    return {"detail": "User removed from group"}


# --- Permissions ---

@router.put("/groups/{group_id}/permissions", response_model=List[GroupPermissionResponse])
def set_group_permissions(
    group_id: int, perm_set: GroupPermissionSet,
    current_user: User = Depends(require_permission("admin", "update")),
    db: Session = Depends(get_db),
):
    db.query(GroupPermission).filter(GroupPermission.group_id == group_id).delete()
    results = []
    for p in perm_set.permissions:
        gp = GroupPermission(group_id=group_id, module=p.module, action=p.action, allowed=p.allowed)
        db.add(gp)
        results.append(gp)
    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/groups/{group_id}/permissions", response_model=List[GroupPermissionResponse])
def get_group_permissions(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(GroupPermission).filter(GroupPermission.group_id == group_id).all()
