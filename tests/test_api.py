import pytest
from fastapi.testclient import TestClient


def test_create_department(client: TestClient):
    """Тест создания подразделения"""
    response = client.post("/departments", json={"name": "IT"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "IT"
    assert data["parent_id"] is None
    assert "id" in data


def test_create_department_duplicate_name(client: TestClient):
    """Тест: нельзя создать два отдела с одинаковым именем внутри одного родителя"""
    client.post("/departments", json={"name": "HR"})
    response = client.post("/departments", json={"name": "HR"})
    assert response.status_code == 409


def test_create_child_department(client: TestClient):
    """Тест создания дочернего подразделения"""
    parent = client.post("/departments", json={"name": "Company"}).json()
    parent_id = parent["id"]
    
    response = client.post("/departments", json={"name": "Backend", "parent_id": parent_id})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Backend"
    assert data["parent_id"] == parent_id


def test_create_employee(client: TestClient):
    """Тест создания сотрудника"""
    dept = client.post("/departments", json={"name": "Dev"}).json()
    dept_id = dept["id"]
    
    response = client.post(f"/departments/{dept_id}/employees", json={
        "full_name": "Иван Иванов",
        "position": "Python Developer"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Иван Иванов"
    assert data["position"] == "Python Developer"
    assert data["department_id"] == dept_id


def test_create_employee_in_nonexistent_department(client: TestClient):
    """Тест: нельзя создать сотрудника в несуществующем отделе"""
    response = client.post("/departments/999/employees", json={
        "full_name": "Тест",
        "position": "Tester"
    })
    assert response.status_code == 404


def test_get_department_tree(client: TestClient):
    """Тест получения дерева подразделений"""
    # Создаём структуру: Company -> IT -> Backend
    response_company = client.post("/departments", json={"name": "Company"})
    assert response_company.status_code == 201
    company = response_company.json()
    company_id = company["id"]
    
    response_it = client.post("/departments", json={"name": "IT", "parent_id": company_id})
    assert response_it.status_code == 201
    it_id = response_it.json()["id"]
    
    response_backend = client.post("/departments", json={"name": "Backend", "parent_id": it_id})
    assert response_backend.status_code == 201
    
    # Создаём сотрудника
    response_emp = client.post(f"/departments/{it_id}/employees", json={
        "full_name": "John Doe",
        "position": "Developer"
    })
    assert response_emp.status_code == 201
    
    # Получаем дерево
    response = client.get(f"/departments/{company_id}?depth=2&include_employees=true")
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Company"
    assert len(data["children"]) == 1
    assert data["children"][0]["name"] == "IT"
    assert len(data["children"][0]["children"]) == 1
    assert data["children"][0]["children"][0]["name"] == "Backend"
    assert len(data["children"][0]["employees"]) == 1


def test_update_department_move(client: TestClient):
    """Тест перемещения подразделения"""
    root = client.post("/departments", json={"name": "Root"}).json()
    child = client.post("/departments", json={"name": "Child", "parent_id": root["id"]}).json()
    new_parent = client.post("/departments", json={"name": "NewParent"}).json()
    
    response = client.patch(f"/departments/{child['id']}", json={"parent_id": new_parent["id"]})
    assert response.status_code == 200
    assert response.json()["parent_id"] == new_parent["id"]


def test_update_department_cycle(client: TestClient):
    """Тест: нельзя создать цикл в дереве"""
    a = client.post("/departments", json={"name": "A"}).json()
    b = client.post("/departments", json={"name": "B", "parent_id": a["id"]}).json()
    c = client.post("/departments", json={"name": "C", "parent_id": b["id"]}).json()
    
    # Пытаемся переместить A внутрь C (создать цикл)
    response = client.patch(f"/departments/{a['id']}", json={"parent_id": c["id"]})
    assert response.status_code == 409


def test_delete_department_cascade(client: TestClient):
    """Тест каскадного удаления"""
    parent = client.post("/departments", json={"name": "Parent"}).json()
    child = client.post("/departments", json={"name": "Child", "parent_id": parent["id"]}).json()
    client.post(f"/departments/{child['id']}/employees", json={
        "full_name": "Employee",
        "position": "Worker"
    })
    
    # Каскадное удаление
    response = client.delete(f"/departments/{parent['id']}?mode=cascade")
    assert response.status_code == 204
    
    # Проверяем, что подразделение удалено
    get_response = client.get(f"/departments/{parent['id']}")
    assert get_response.status_code == 404


def test_delete_department_reassign(client: TestClient):
    """Тест удаления с переназначением сотрудников"""
    old_parent = client.post("/departments", json={"name": "OldDept"}).json()
    new_parent = client.post("/departments", json={"name": "NewDept"}).json()
    
    # Создаём сотрудника
    emp_response = client.post(f"/departments/{old_parent['id']}/employees", json={
        "full_name": "Reassigned Employee",
        "position": "Worker"
    })
    assert emp_response.status_code == 201
    employee_id = emp_response.json()["id"]
    
    # Удаляем с переназначением
    response = client.delete(f"/departments/{old_parent['id']}?mode=reassign&reassign_to_department_id={new_parent['id']}")
    assert response.status_code == 204
    
    # Проверяем, что сотрудник теперь в новом отделе
    get_response = client.get(f"/departments/{new_parent['id']}?include_employees=true")
    assert get_response.status_code == 200
    assert len(get_response.json()["employees"]) == 1
    assert get_response.json()["employees"][0]["id"] == employee_id