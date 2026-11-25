import pytest
from fastapi.testclient import TestClient


def make_category(
    client: TestClient, name: str = "Tools", **overrides: object
) -> dict:
    response = client.post("/api/categories", json={"name": name, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_category(client: TestClient) -> None:
    created = make_category(
        client,
        name="  Tools  ",
        description="  Hardware tools  ",
    )

    assert created["id"] >= 1
    assert created["name"] == "Tools"
    assert created["description"] == "Hardware tools"
    assert created["product_count"] == 0
    assert created["created_at"] and created["updated_at"]


def test_create_category_empty_description_becomes_none(client: TestClient) -> None:
    created = make_category(client, name="Tools", description="   ")

    assert created["description"] is None


def test_duplicate_category_name_conflict(client: TestClient) -> None:
    make_category(client, name="tools")

    response = client.post("/api/categories", json={"name": "TOOLS"})

    assert response.status_code == 409


def test_list_categories_with_product_count_and_search(client: TestClient) -> None:
    first = make_category(client, name="Tools", description="hand tools")
    make_category(client, name="Office", description="stationery")
    response = client.post(
        "/api/products", json={"sku": "T-1", "name": "Hammer", "category_id": first["id"]}
    )
    assert response.status_code == 201

    listing = client.get("/api/categories")
    assert [item["name"] for item in listing.json()] == ["Office", "Tools"]
    tools = next(item for item in listing.json() if item["name"] == "Tools")
    assert tools["product_count"] == 1

    search = client.get("/api/categories", params={"q": "STATIONERY"})
    assert [item["name"] for item in search.json()] == ["Office"]

    wildcard = client.get("/api/categories", params={"q": "%"})
    assert wildcard.json() == []


def test_get_category(client: TestClient) -> None:
    created = make_category(client)

    response = client.get(f"/api/categories/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Tools"


def test_get_category_not_found(client: TestClient) -> None:
    assert client.get("/api/categories/999").status_code == 404


def test_patch_category(client: TestClient) -> None:
    created = make_category(client, description="Old")

    response = client.patch(
        f"/api/categories/{created['id']}",
        json={"name": "  New Tools  ", "description": "  New  "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Tools"
    assert body["description"] == "New"


def test_patch_category_not_found(client: TestClient) -> None:
    assert client.patch("/api/categories/999", json={"name": "Ghost"}).status_code == 404


def test_patch_category_duplicate_name_conflict(client: TestClient) -> None:
    make_category(client, name="ONE")
    second = make_category(client, name="TWO")

    response = client.patch(f"/api/categories/{second['id']}", json={"name": "one"})

    assert response.status_code == 409


def test_patch_category_name_cannot_be_null(client: TestClient) -> None:
    created = make_category(client)

    response = client.patch(f"/api/categories/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_delete_category_clears_product_reference(client: TestClient) -> None:
    category = make_category(client)
    product_response = client.post(
        "/api/products",
        json={"sku": "C-1", "name": "Widget", "category_id": category["id"]},
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    deleted = client.delete(f"/api/categories/{category['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/api/categories/{category['id']}").status_code == 404
    body = client.get(f"/api/products/{product_id}").json()
    assert body["category_id"] is None
    assert body["category"] is None


def test_delete_category_not_found(client: TestClient) -> None:
    assert client.delete("/api/categories/999").status_code == 404


@pytest.mark.parametrize(
    ("field", "length"), [("name", 101), ("description", 501)]
)
def test_category_max_lengths(client: TestClient, field: str, length: int) -> None:
    payload = {"name": "Tools", field: "x" * length}

    assert client.post("/api/categories", json=payload).status_code == 422

    created = make_category(client)
    assert client.patch(f"/api/categories/{created['id']}", json=payload).status_code == 422
