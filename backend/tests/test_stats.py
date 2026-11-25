from fastapi.testclient import TestClient


def setup_data(client: TestClient) -> None:
    electronics = client.post("/api/categories", json={"name": "Electronics"}).json()
    office = client.post("/api/categories", json={"name": "Office"}).json()
    supplier = client.post("/api/suppliers", json={"name": "Acme Supply"}).json()

    specs = [
        {
            "sku": "S1",
            "name": "Lamp",
            "quantity": 10,
            "reorder_level": 5,
            "cost_price": "2.00",
            "sell_price": "5.00",
            "category_id": electronics["id"],
            "supplier_id": supplier["id"],
        },
        {
            "sku": "S2",
            "name": "Mouse",
            "quantity": 4,
            "reorder_level": 5,
            "cost_price": "1.50",
            "sell_price": "4.00",
            "category_id": electronics["id"],
        },
        {
            "sku": "S3",
            "name": "Cable",
            "quantity": 0,
            "reorder_level": 2,
            "cost_price": "9.00",
            "sell_price": "20.00",
            "category_id": office["id"],
        },
        {
            "sku": "S4",
            "name": "Inactive",
            "quantity": 7,
            "reorder_level": 1,
            "cost_price": "1.00",
            "sell_price": "3.00",
            "is_active": False,
        },
    ]
    products = []
    for spec in specs:
        response = client.post("/api/products", json=spec)
        assert response.status_code == 201, response.text
        products.append(response.json())

    for product_id, movement_type, quantity in (
        (products[0]["id"], "IN", 2),
        (products[1]["id"], "OUT", 1),
        (products[2]["id"], "ADJUST", 0),
    ):
        response = client.post(
            f"/api/products/{product_id}/movements",
            json={"movement_type": movement_type, "quantity": quantity},
        )
        assert response.status_code == 201, response.text


def test_stats_empty_database(client: TestClient) -> None:
    body = client.get("/api/stats").json()

    assert body == {
        "total_products": 0,
        "active_products": 0,
        "total_stock_units": 0,
        "stock_cost_value": 0.0,
        "stock_retail_value": 0.0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
        "category_count": 0,
        "supplier_count": 0,
        "recent_movements": [],
    }


def test_stats_all_fields(client: TestClient) -> None:
    setup_data(client)

    body = client.get("/api/stats").json()

    assert body["total_products"] == 4
    assert body["active_products"] == 3
    assert body["total_stock_units"] == 22
    assert body["stock_cost_value"] == 35.5
    assert body["stock_retail_value"] == 93.0
    assert body["low_stock_count"] == 1  # Mouse: 3 <= 5, zero excluded
    assert body["out_of_stock_count"] == 1  # Cable
    assert body["category_count"] == 2
    assert body["supplier_count"] == 1

    for field in (
        "total_products",
        "active_products",
        "total_stock_units",
        "low_stock_count",
        "out_of_stock_count",
        "category_count",
        "supplier_count",
    ):
        assert isinstance(body[field], int)
    for field in ("stock_cost_value", "stock_retail_value"):
        assert isinstance(body[field], float)

    recent = body["recent_movements"]
    assert [item["movement_type"] for item in recent] == ["ADJUST", "OUT", "IN"]
    assert [item["product"]["sku"] for item in recent] == ["S3", "S2", "S1"]
    assert recent[1]["product"]["name"] == "Mouse"


def test_stats_recent_movements_limited_to_ten(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "S1", "name": "Widget", "quantity": 50}
    ).json()
    for index in range(12):
        response = client.post(
            f"/api/products/{product['id']}/movements",
            json={"movement_type": "OUT", "quantity": 1, "note": f"sale {index}"},
        )
        assert response.status_code == 201

    recent = client.get("/api/stats").json()["recent_movements"]

    assert len(recent) == 10
    assert [item["note"] for item in recent] == [f"sale {i}" for i in range(11, 1, -1)]
