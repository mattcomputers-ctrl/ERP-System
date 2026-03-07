from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class UserGroupAssociation(Base):
    __tablename__ = "user_group_associations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    groups = relationship("UserGroup", secondary="user_group_associations", back_populates="users")


class UserGroup(Base):
    __tablename__ = "user_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    users = relationship("User", secondary="user_group_associations", back_populates="groups")
    permissions = relationship("GroupPermission", back_populates="group", cascade="all, delete-orphan")


class GroupPermission(Base):
    __tablename__ = "group_permissions"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    module = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    allowed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("UserGroup", back_populates="permissions")
    __table_args__ = (UniqueConstraint("group_id", "module", "action", name="uq_group_module_action"),)
