import importlib
import os

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_inventory.db"
    monkeypatch.setenv("INVENTORY_DB", str(db_path))

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_product_lifecycle(client):
    create = client.post(
        "/api/products",
        json={
            "sku": "TEST-001",
            "name": "Test Product",
            "price": 49.9,
            "stock": 10,
            "low_stock_threshold": 3,
        },
    )
    assert create.status_code == 201
    product = create.get_json()
    product_id = product["id"]
    assert product["stock"] == 10

    stock_out = client.post(
        f"/api/products/{product_id}/stock",
        json={"type": "out", "quantity": 8, "note": "Test order"},
    )
    assert stock_out.status_code == 200
    assert stock_out.get_json()["stock"] == 2
    assert stock_out.get_json()["is_low_stock"] is True

    low_stock = client.get("/api/low-stock")
    assert low_stock.status_code == 200
    assert any(item["id"] == product_id for item in low_stock.get_json())

    movements = client.get(f"/api/products/{product_id}/movements")
    assert movements.status_code == 200
    assert len(movements.get_json()) >= 2


def test_duplicate_sku_is_rejected(client):
    payload = {"sku": "DUP-001", "name": "First", "price": 10}
    assert client.post("/api/products", json=payload).status_code == 201

    duplicate = client.post(
        "/api/products",
        json={"sku": "DUP-001", "name": "Second", "price": 20},
    )
    assert duplicate.status_code == 409


def test_negative_stock_is_prevented(client):
    create = client.post(
        "/api/products",
        json={"sku": "STOCK-001", "name": "Stock Test", "price": 15, "stock": 2},
    )
    product_id = create.get_json()["id"]

    response = client.post(
        f"/api/products/{product_id}/stock",
        json={"type": "out", "quantity": 3},
    )
    assert response.status_code == 409
    assert response.get_json()["error"] == "Insufficient stock"
