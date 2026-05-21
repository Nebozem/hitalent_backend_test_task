from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app import schemas, crud, models
from app.database import get_db

router = APIRouter()


# Вспомогательная функция для построения дерева
def build_tree(
    db: Session,
    department_id: int,
    depth: int,
    current_depth: int,
    include_employees: bool
) -> schemas.DepartmentTreeResponse:
    department = crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    result = schemas.DepartmentTreeResponse(
        id=department.id,
        name=department.name,
        parent_id=department.parent_id,
        created_at=department.created_at,
        children=[],
        employees=[]
    )

    if include_employees:
        employees = crud.get_employees_by_department(db, department_id)
        result.employees = [schemas.EmployeeResponse.model_validate(emp) for emp in employees]

    if current_depth < depth:
        children = db.query(models.Department).filter(
            models.Department.parent_id == department_id
        ).all()
        for child in children:
            child_tree = build_tree(db, child.id, depth, current_depth + 1, include_employees)
            result.children.append(child_tree)

    return result


# 1. Создать подразделение
@router.post("/", response_model=schemas.DepartmentResponse, status_code=201)
def create_department(
    department: schemas.DepartmentCreate,
    db: Session = Depends(get_db)
):
    # Проверка уникальности имени среди sibling'ов
    existing = crud.get_department_by_name(db, department.name, department.parent_id)
    if existing:
        raise HTTPException(status_code=409, detail="Department with this name already exists in the same parent")

    # Проверка существования родителя
    if department.parent_id:
        parent = crud.get_department(db, department.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent department not found")

    return crud.create_department(db, department)


# 2. Создать сотрудника в подразделении
@router.post("/{department_id}/employees", response_model=schemas.EmployeeResponse, status_code=201)
def create_employee(
    department_id: int,
    employee: schemas.EmployeeCreate,
    db: Session = Depends(get_db)
):
    department = crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return crud.create_employee(db, department_id, employee)


# 3. Получить подразделение (с деревом и сотрудниками)
@router.get("/{department_id}", response_model=schemas.DepartmentTreeResponse)
def get_department(
    department_id: int,
    depth: int = Query(1, ge=1, le=5),
    include_employees: bool = Query(True),
    db: Session = Depends(get_db)
):
    return build_tree(db, department_id, depth, 1, include_employees)


# 4. Переместить подразделение (изменить parent_id)
@router.patch("/{department_id}", response_model=schemas.DepartmentResponse)
def update_department(
    department_id: int,
    department_update: schemas.DepartmentUpdate,
    db: Session = Depends(get_db)
):
    # Проверка существования
    department = crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Проверка уникальности имени (если меняем)
    if department_update.name:
        existing = crud.get_department_by_name(db, department_update.name, department_update.parent_id)
        if existing and existing.id != department_id:
            raise HTTPException(status_code=409, detail="Department with this name already exists in the same parent")

    # Проверка parent (если меняем)
    if department_update.parent_id is not None:
        # Нельзя сделать родителем самого себя
        if department_update.parent_id == department_id:
            raise HTTPException(status_code=409, detail="Department cannot be parent of itself")

        # Проверка на цикл
        parent_id = department_update.parent_id
        visited = set()
        while parent_id is not None:
            if parent_id == department_id:
                raise HTTPException(status_code=409, detail="Cannot move department into its own child")
            if parent_id in visited:
                break
            visited.add(parent_id)
            parent = crud.get_department(db, parent_id)
            parent_id = parent.parent_id if parent else None

    return crud.update_department(db, department_id, department_update)


# 5. Удалить подразделение
@router.delete("/{department_id}", status_code=204)
def delete_department(
    department_id: int,
    mode: str = Query(..., pattern="^(cascade|reassign)$"),
    reassign_to_department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    department = crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    if mode == "reassign":
        if not reassign_to_department_id:
            raise HTTPException(status_code=400, detail="reassign_to_department_id is required for reassign mode")

        target = crud.get_department(db, reassign_to_department_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target department not found")

        # Переназначаем сотрудников
        crud.reassign_employees(db, department_id, reassign_to_department_id)
        # Переназначаем дочерние подразделения
        crud.reassign_children_departments(db, department_id, reassign_to_department_id)
        # Удаляем само подразделение
        crud.delete_department(db, department_id)

    elif mode == "cascade":
        # Каскадное удаление через ondelete=CASCADE в БД
        crud.delete_department(db, department_id)

    return None