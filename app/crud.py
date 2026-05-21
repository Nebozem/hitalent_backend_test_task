from sqlalchemy.orm import Session
from sqlalchemy import asc
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from app import models, schemas


def get_department(db: Session, department_id: int) -> Optional[models.Department]:
    return db.query(models.Department).filter(models.Department.id == department_id).first()

def get_department_by_name(db: Session, name: str, parent_id: Optional[int] = None) -> Optional[models.Department]:
    return db.query(models.Department).filter(
        models.Department.name == name,
        models.Department.parent_id == parent_id
    ).first()

def create_department(db: Session, department: schemas.DepartmentCreate) -> models.Department:
    db_department = models.Department(name=department.name, parent_id=department.parent_id)
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    return db_department

def update_department(db: Session, department_id: int, department_update: schemas.DepartmentUpdate) -> Optional[models.Department]:
    db_department = get_department(db, department_id)
    if not db_department:
        return None
    
    update_data = department_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_department, field, value)
    
    db.commit()
    db.refresh(db_department)
    return db_department

def delete_department(db: Session, department_id: int) -> bool:
    db_department = get_department(db, department_id)
    if not db_department:
        return False
    db.delete(db_department)
    db.commit()
    return True

def get_children_ids(db: Session, department_id: int) -> List[int]:
    """Рекурсивно получить все ID дочерних подразделений"""
    children = db.query(models.Department).filter(models.Department.parent_id == department_id).all()
    ids = [child.id for child in children]
    for child in children:
        ids.extend(get_children_ids(db, child.id))
    return ids

def create_employee(db: Session, department_id: int, employee: schemas.EmployeeCreate) -> models.Employee:
    db_employee = models.Employee(
        department_id=department_id,
        full_name=employee.full_name,
        position=employee.position,
        hired_at=employee.hired_at
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def get_employees_by_department(db: Session, department_id: int) -> List[models.Employee]:
    return db.query(models.Employee).filter(
        models.Employee.department_id == department_id
    ).order_by(asc(models.Employee.created_at)).all()

def reassign_employees(db: Session, from_department_id: int, to_department_id: int):
    db.query(models.Employee).filter(
        models.Employee.department_id == from_department_id
    ).update({"department_id": to_department_id})
    db.commit()

def reassign_children_departments(db: Session, from_parent_id: int, to_parent_id: int):
    db.query(models.Department).filter(
        models.Department.parent_id == from_parent_id
    ).update({"parent_id": to_parent_id})
    db.commit()