import pytest
from fastapi.testclient import TestClient


def make_supplier(client: TestClient, name: str = "Acme", **overrides: object) -> dict:
    response = client.post("/api/suppliers", json={"name": name, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_supplier(client: TestClient) -> None:
    created = make_supplier(
        client,
        name="  Acme  ",
        contact_name="  Jane Doe  ",
        email="  jane@example.com  ",
        phone="  555-0100  ",
        address="  1 Main St  ",
        notes="  Preferred vendor  ",
    )

    assert created["id"] >= 1
    assert created["name"] == "Acme"
    assert created["contact_name"] == "Jane Doe"
    assert created["email"] == "jane@example.com"
    assert created["phone"] == "555-0100"
    assert created["address"] == "1 Main St"
    assert created["notes"] == "Preferred vendor"
    assert created["product_count"] == 0
    assert created["created_at"] and created["updated_at"]


def test_create_supplier_empty_optionals_become_none(client: TestClient) -> None:
    created = make_supplier(
        client,
        name="Acme",
        contact_name="  ",
        email=" ",
        phone=" ",
        address=" ",
        notes=" ",
    )

    assert all(
        created[field] is None
        for field in ("contact_name", "email", "phone", "address", "notes")
    )


def test_duplicate_supplier_name_conflict(client: TestClient) -> None:
    make_supplier(client, name="acme")

    assert client.post("/api/suppliers", json={"name": "ACME"}).status_code == 409


def test_list_suppliers_with_product_count_and_search(client: TestClient) -> None:
    first = make_supplier(client, name="Acme", notes="fast shipping")
    make_supplier(client, name="Globex", notes="slow shipping")
    response = client.post(
        "/api/products",
        json={"sku": "S-1", "name": "Widget", "supplier_id": first["id"]},
    )
    assert response.status_code == 201

    listing = client.get("/api/suppliers")
    assert [item["name"] for item in listing.json()] == ["Acme", "Globex"]
    acme = next(item for item in listing.json() if item["name"] == "Acme")
    assert acme["product_count"] == 1

    search = client.get("/api/suppliers", params={"q": "FAST SHIPPING"})
    assert [item["name"] for item in search.json()] == ["Acme"]

    assert client.get("/api/suppliers", params={"q": "%"}).json() == []


def test_get_supplier(client: TestClient) -> None:
    created = make_supplier(client)

    response = client.get(f"/api/suppliers/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Acme"


def test_get_supplier_not_found(client: TestClient) -> None:
    assert client.get("/api/suppliers/999").status_code == 404


def test_patch_supplier(client: TestClient) -> None:
    created = make_supplier(client)

    response = client.patch(
        f"/api/suppliers/{created['id']}",
        json={"name": "  Acme Ltd  ", "phone": "  555-0200  "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Ltd"
    assert body["phone"] == "555-0200"


def test_patch_supplier_not_found(client: TestClient) -> None:
    assert client.patch("/api/suppliers/999", json={"name": "Ghost"}).status_code == 404


def test_patch_supplier_duplicate_name_conflict(client: TestClient) -> None:
    make_supplier(client, name="ONE")
    second = make_supplier(client, name="TWO")

    assert (
        client.patch(f"/api/suppliers/{second['id']}", json={"name": "one"}).status_code
        == 409
    )


def test_patch_supplier_name_cannot_be_null(client: TestClient) -> None:
    created = make_supplier(client)

    assert (
        client.patch(f"/api/suppliers/{created['id']}", json={"name": None}).status_code
        == 422
    )


def test_delete_supplier_clears_product_reference(client: TestClient) -> None:
    supplier = make_supplier(client)
    response = client.post(
        "/api/products",
        json={"sku": "S-1", "name": "Widget", "supplier_id": supplier["id"]},
    )
    assert response.status_code == 201
    product_id = response.json()["id"]

    deleted = client.delete(f"/api/suppliers/{supplier['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/api/suppliers/{supplier['id']}").status_code == 404
    body = client.get(f"/api/products/{product_id}").json()
    assert body["supplier_id"] is None
    assert body["supplier"] is None


def test_delete_supplier_not_found(client: TestClient) -> None:
    assert client.delete("/api/suppliers/999").status_code == 404


@pytest.mark.parametrize(
    ("field", "length"),
    [
        ("name", 201),
        ("contact_name", 201),
        ("email", 201),
        ("phone", 51),
        ("address", 501),
        ("notes", 1001),
    ],
)
def test_supplier_max_lengths(client: TestClient, field: str, length: int) -> None:
    payload = {"name": "Acme", field: "x" * length}

    assert client.post("/api/suppliers", json=payload).status_code == 422

    created = make_supplier(client)
    assert client.patch(f"/api/suppliers/{created['id']}", json=payload).status_code == 422
