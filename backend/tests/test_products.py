from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


def make_product(
    client: TestClient,
    sku: str = "SKU-1",
    name: str = "Widget",
    **overrides: object,
) -> dict:
    payload = {"sku": sku, "name": name, **overrides}
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_product(client: TestClient) -> None:
    created = make_product(
        client,
        sku=" sku-1 ",
        name="  Widget  ",
        description="  A useful widget  ",
        cost_price="3.50",
        sell_price="9.99",
        quantity=4,
        reorder_level=2,
    )

    assert created["id"] >= 1
    assert created["sku"] == "SKU-1"
    assert created["name"] == "Widget"
    assert created["description"] == "A useful widget"
    assert isinstance(created["cost_price"], float)
    assert isinstance(created["sell_price"], float)
    assert Decimal(str(created["cost_price"])) == Decimal("3.50")
    assert Decimal(str(created["sell_price"])) == Decimal("9.99")
    assert created["quantity"] == 4
    assert created["reorder_level"] == 2
    assert created["is_active"] is True
    assert created["created_at"] and created["updated_at"]


def test_create_product_defaults(client: TestClient) -> None:
    created = make_product(client)

    assert created["description"] is None
    assert isinstance(created["cost_price"], float)
    assert isinstance(created["sell_price"], float)
    assert Decimal(str(created["cost_price"])) == 0
    assert Decimal(str(created["sell_price"])) == 0
    assert created["quantity"] == 0
    assert created["reorder_level"] == 0
    assert created["is_active"] is True


def test_duplicate_sku_conflict(client: TestClient) -> None:
    make_product(client, sku="abc")
    response = client.post("/api/products", json={"sku": "ABC", "name": "Other"})

    assert response.status_code == 409


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "pages": 0,
    }


def test_list_paginated(client: TestClient) -> None:
    for index in range(3):
        make_product(client, sku=f"SKU-{index}", name=f"Widget {index}")

    response = client.get("/api/products", params={"page": 2, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["sku"] == "SKU-2"
    assert isinstance(body["items"][0]["cost_price"], float)
    assert isinstance(body["items"][0]["sell_price"], float)
    assert Decimal(str(body["items"][0]["cost_price"])) == 0
    assert Decimal(str(body["items"][0]["sell_price"])) == 0


def test_search_by_name_and_sku(client: TestClient) -> None:
    make_product(client, sku="SKU-1", name="Blue Widget", description="first")
    make_product(client, sku="SKU-2", name="Red Gadget", description="second")

    by_name = client.get("/api/products", params={"q": "widget"})
    by_sku = client.get("/api/products", params={"q": "SKU-1"})
    by_description = client.get("/api/products", params={"q": "SECOND"})

    assert [item["sku"] for item in by_name.json()["items"]] == ["SKU-1"]
    assert [item["sku"] for item in by_sku.json()["items"]] == ["SKU-1"]
    assert [item["sku"] for item in by_description.json()["items"]] == ["SKU-2"]


def test_sort_by_quantity_descending(client: TestClient) -> None:
    make_product(client, sku="SKU-LOW", name="Low", quantity=2)
    make_product(client, sku="SKU-HIGH", name="High", quantity=20)

    response = client.get("/api/products", params={"sort": "-quantity"})

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == ["SKU-HIGH", "SKU-LOW"]


def test_invalid_sort(client: TestClient) -> None:
    response = client.get("/api/products", params={"sort": "unknown"})

    assert response.status_code == 422


def test_low_stock_filter(client: TestClient) -> None:
    make_product(client, sku="SKU-LOW", name="Low", quantity=5, reorder_level=10)
    make_product(client, sku="SKU-OK", name="Ok", quantity=5, reorder_level=2)

    response = client.get("/api/products", params={"low_stock": "true"})

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == ["SKU-LOW"]


def test_get_product(client: TestClient) -> None:
    created = make_product(client)
    response = client.get(f"/api/products/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "SKU-1"
    assert isinstance(body["cost_price"], float)
    assert isinstance(body["sell_price"], float)
    assert Decimal(str(body["cost_price"])) == 0
    assert Decimal(str(body["sell_price"])) == 0


def test_get_product_not_found(client: TestClient) -> None:
    response = client.get("/api/products/999")

    assert response.status_code == 404


def test_patch_product(client: TestClient) -> None:
    created = make_product(client, quantity=1)
    response = client.patch(
        f"/api/products/{created['id']}",
        json={"name": "  New Name  ", "quantity": 42, "is_active": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["quantity"] == 42
    assert body["is_active"] is False
    assert body["sku"] == "SKU-1"
    assert client.get(f"/api/products/{created['id']}").json()["name"] == "New Name"


def test_patch_product_not_found(client: TestClient) -> None:
    response = client.patch("/api/products/999", json={"name": "Ghost"})

    assert response.status_code == 404


def test_patch_duplicate_sku_conflict(client: TestClient) -> None:
    first = make_product(client, sku="ONE")
    second = make_product(client, sku="TWO")

    response = client.patch(f"/api/products/{second['id']}", json={"sku": "one"})

    assert response.status_code == 409
    assert client.get(f"/api/products/{first['id']}").json()["sku"] == "ONE"


def test_delete_product(client: TestClient) -> None:
    created = make_product(client)

    response = client.delete(f"/api/products/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/products/{created['id']}").status_code == 404


def test_delete_product_not_found(client: TestClient) -> None:
    assert client.delete("/api/products/999").status_code == 404


def test_validation_negative_price(client: TestClient) -> None:
    response = client.post(
        "/api/products", json={"sku": "SKU-1", "name": "Widget", "cost_price": -1}
    )

    assert response.status_code == 422


def test_validation_empty_name(client: TestClient) -> None:
    response = client.post("/api/products", json={"sku": "SKU-1", "name": "   "})

    assert response.status_code == 422


def test_validation_page_size_too_large(client: TestClient) -> None:
    response = client.get("/api/products", params={"page_size": 101})

    assert response.status_code == 422


def test_duplicate_sku_integrity_error_returns_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_product(client, sku="UNIQUE-1")
    monkeypatch.setattr(
        "app.services.products._ensure_unique_sku",
        lambda *args, **kwargs: None,
    )

    response = client.post("/api/products", json={"sku": "UNIQUE-1", "name": "Other"})

    assert response.status_code == 409
    assert response.json()["detail"] == "A product with this SKU already exists"


@pytest.mark.parametrize(
    ("field", "length"),
    [("sku", 65), ("name", 201), ("description", 2001)],
)
def test_create_rejects_overlong_fields(
    client: TestClient, field: str, length: int
) -> None:
    payload = {"sku": "SKU-1", "name": "Widget", field: "x" * length}

    response = client.post("/api/products", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "length"),
    [("sku", 65), ("name", 201), ("description", 2001)],
)
def test_update_rejects_overlong_fields(
    client: TestClient, field: str, length: int
) -> None:
    created = make_product(client)

    response = client.patch(
        f"/api/products/{created['id']}", json={field: "x" * length}
    )

    assert response.status_code == 422


def test_search_escapes_percent_wildcard(client: TestClient) -> None:
    make_product(client, sku="SKU-P", name="100% Cotton")
    make_product(client, sku="SKU-X", name="100X Cotton")

    response = client.get("/api/products", params={"q": "100%"})

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == ["SKU-P"]


def test_search_escapes_underscore_wildcard(client: TestClient) -> None:
    make_product(client, sku="SKU-U", name="A_B")
    make_product(client, sku="SKU-X", name="AXB")

    response = client.get("/api/products", params={"q": "A_B"})

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == ["SKU-U"]


@pytest.mark.parametrize("page", [0, -1])
def test_invalid_page(client: TestClient, page: int) -> None:
    response = client.get("/api/products", params={"page": page})

    assert response.status_code == 422


def test_low_stock_includes_equal_threshold(client: TestClient) -> None:
    make_product(client, sku="SKU-EQ", name="Equal", quantity=5, reorder_level=5)
    make_product(client, sku="SKU-OK", name="Ok", quantity=6, reorder_level=5)

    response = client.get("/api/products", params={"low_stock": "true"})

    assert [item["sku"] for item in response.json()["items"]] == ["SKU-EQ"]


def test_patch_description_null_clears(client: TestClient) -> None:
    created = make_product(client, description="Original description")

    response = client.patch(
        f"/api/products/{created['id']}", json={"description": None}
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert client.get(f"/api/products/{created['id']}").json()["description"] is None


@pytest.mark.parametrize(
    "sort",
    ["id", "sku", "name", "quantity", "sell_price", "created_at"],
)
def test_all_sort_keys(client: TestClient, sort: str) -> None:
    make_product(client, sku="SKU-1", name="Widget", quantity=2)

    assert client.get("/api/products", params={"sort": sort}).status_code == 200
    assert client.get("/api/products", params={"sort": f"-{sort}"}).status_code == 200
