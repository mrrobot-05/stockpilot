from fastapi.testclient import TestClient


def make_refs(client: TestClient) -> tuple[dict, dict, dict, dict]:
    category_a = client.post("/api/categories", json={"name": "Tools"}).json()
    category_b = client.post("/api/categories", json={"name": "Office"}).json()
    supplier_x = client.post("/api/suppliers", json={"name": "Acme"}).json()
    supplier_y = client.post("/api/suppliers", json={"name": "Globex"}).json()
    return category_a, category_b, supplier_x, supplier_y


def test_create_product_with_refs_returns_nested_read(client: TestClient) -> None:
    category, _, supplier, _ = make_refs(client)

    response = client.post(
        "/api/products",
        json={
            "sku": "REF-1",
            "name": "Hammer",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] == category["id"]
    assert body["supplier_id"] == supplier["id"]
    assert body["category"] == {"id": category["id"], "name": "Tools"}
    assert body["supplier"] == {"id": supplier["id"], "name": "Acme"}

    fetched = client.get(f"/api/products/{body['id']}")
    assert fetched.json()["category"] == {"id": category["id"], "name": "Tools"}
    assert fetched.json()["supplier"] == {"id": supplier["id"], "name": "Acme"}


def test_create_product_invalid_refs(client: TestClient) -> None:
    bad_category = client.post(
        "/api/products", json={"sku": "BAD-1", "name": "One", "category_id": 999}
    )
    bad_supplier = client.post(
        "/api/products", json={"sku": "BAD-2", "name": "Two", "supplier_id": 999}
    )

    assert bad_category.status_code == 422
    assert bad_supplier.status_code == 422
    assert "Category 999" in bad_category.json()["detail"]
    assert "Supplier 999" in bad_supplier.json()["detail"]


def test_list_products_filters(client: TestClient) -> None:
    category_a, category_b, supplier_x, supplier_y = make_refs(client)
    for sku, category_id, supplier_id, is_active in (
        ("P-1", category_a["id"], supplier_x["id"], True),
        ("P-2", category_a["id"], supplier_y["id"], False),
        ("P-3", category_b["id"], supplier_x["id"], True),
    ):
        response = client.post(
            "/api/products",
            json={
                "sku": sku,
                "name": f"Product {sku}",
                "category_id": category_id,
                "supplier_id": supplier_id,
                "is_active": is_active,
            },
        )
        assert response.status_code == 201

    def skus(params: dict) -> list[str]:
        body = client.get("/api/products", params=params).json()
        return [item["sku"] for item in body["items"]]

    assert skus({"category_id": category_a["id"]}) == ["P-1", "P-2"]
    assert skus({"category_id": category_b["id"]}) == ["P-3"]
    assert skus({"supplier_id": supplier_x["id"]}) == ["P-1", "P-3"]
    assert skus({"supplier_id": supplier_y["id"]}) == ["P-2"]
    assert skus({"is_active": "false"}) == ["P-2"]
    assert skus({"is_active": "true"}) == ["P-1", "P-3"]
    assert skus(
        {"category_id": category_a["id"], "is_active": "false"}
    ) == ["P-2"]


def test_patch_product_refs_and_clear(client: TestClient) -> None:
    category, _, supplier, _ = make_refs(client)
    product = client.post("/api/products", json={"sku": "REF-2", "name": "Drill"}).json()

    patched = client.patch(
        f"/api/products/{product['id']}",
        json={"category_id": category["id"], "supplier_id": supplier["id"]},
    )
    assert patched.status_code == 200
    assert patched.json()["category"]["name"] == "Tools"
    assert patched.json()["supplier"]["name"] == "Acme"

    cleared = client.patch(
        f"/api/products/{product['id']}",
        json={"category_id": None, "supplier_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["category_id"] is None
    assert cleared.json()["supplier_id"] is None
    assert cleared.json()["category"] is None
    assert cleared.json()["supplier"] is None


def test_patch_product_invalid_ref(client: TestClient) -> None:
    product = client.post("/api/products", json={"sku": "REF-3", "name": "Saw"}).json()

    response = client.patch(
        f"/api/products/{product['id']}", json={"category_id": 999}
    )

    assert response.status_code == 422
    assert client.get(f"/api/products/{product['id']}").json()["category_id"] is None
