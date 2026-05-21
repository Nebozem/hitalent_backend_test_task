from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List

# Схемы для Department
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    parent_id: Optional[int] = None

class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Рекурсивная схема для дерева
class DepartmentTreeResponse(DepartmentResponse):
    children: List["DepartmentTreeResponse"] = Field(default_factory=list)
    employees: List["EmployeeResponse"] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)

# Схемы для Employee
class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: Optional[date] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: Optional[date]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Для рекурсивной схемы
DepartmentTreeResponse.model_rebuild()