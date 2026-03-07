from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GLAccountMappingBase(BaseModel):
    account_type: str
    account_name: str
    account_number: Optional[str] = None
    qb_account_ref: Optional[str] = None


class GLAccountMappingResponse(GLAccountMappingBase):
    id: int
    gl_group_id: int

    class Config:
        from_attributes = True


class GLGroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GLGroupCreate(GLGroupBase):
    account_mappings: Optional[List[GLAccountMappingBase]] = []


class GLGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GLGroupResponse(GLGroupBase):
    id: int
    created_at: datetime
    account_mappings: List[GLAccountMappingResponse] = []

    class Config:
        from_attributes = True
