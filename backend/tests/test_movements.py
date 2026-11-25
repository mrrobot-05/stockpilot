import pytest
from fastapi.testclient import TestClient


def make_product(client: TestClient, sku: str = "MOV-1", quantity: int = 0) -> dict:
    response = client.post(
        "/api/products", json={"sku": sku, "name": "Widget", "quantity": quantity}
    )
    assert response.status_code == 201, response.text
    return response.json()


def move(
    client: TestClient,
    product_id: int,
    movement_type: str,
    quantity: int,
    note: str | None = None,
):
    payload = {"movement_type": movement_type, "quantity": quantity}
    if note is not None:
        payload["note"] = note
    return client.post(f"/api/products/{product_id}/movements", json=payload)


def history(client: TestClient, product_id: int | None = None) -> dict:
    params = {} if product_id is None else {"product_id": product_id}
    return client.get("/api/movements", params=params).json()


def test_in_movement_adds_stock(client: TestClient) -> None:
    product = make_product(client, quantity=5)

    response = move(client, product["id"], "IN", 7, note="  delivery  ")

    assert response.status_code == 201
    body = response.json()
    assert body["movement_type"] == "IN"
    assert body["quantity"] == 7
    assert body["quantity_change"] == 7
    assert body["stock_after"] == 12
    assert body["note"] == "delivery"
    assert body["product_id"] == product["id"]
    assert body["product"] == {
        "id": product["id"],
        "sku": "MOV-1",
        "name": "Widget",
    }
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 12


def test_out_movement_subtracts_stock(client: TestClient) -> None:
    product = make_product(client, quantity=10)

    response = move(client, product["id"], "OUT", 4)

    assert response.status_code == 201
    body = response.json()
    assert body["movement_type"] == "OUT"
    assert body["quantity"] == 4
    assert body["quantity_change"] == -4
    assert body["stock_after"] == 6
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 6


def test_insufficient_out_conflict_leaves_no_trace(client: TestClient) -> None:
    product = make_product(client, quantity=3)

    response = move(client, product["id"], "OUT", 4)

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient stock"
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 3
    assert history(client, product["id"])["total"] == 0


@pytest.mark.parametrize(
    ("opening", "adjust_to", "expected_change", "expected_stock"),
    [(10, 4, -6, 4), (10, 20, 10, 20), (5, 0, -5, 0), (0, 0, 0, 0)],
)
def test_adjust_sets_absolute_stock(
    client: TestClient,
    opening: int,
    adjust_to: int,
    expected_change: int,
    expected_stock: int,
) -> None:
    product = make_product(client, sku=f"ADJ-{opening}-{adjust_to}", quantity=opening)

    response = move(client, product["id"], "ADJUST", adjust_to)

    assert response.status_code == 201
    body = response.json()
    assert body["quantity"] == adjust_to
    assert body["quantity_change"] == expected_change
    assert body["stock_after"] == expected_stock
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == expected_stock


@pytest.mark.parametrize(
    ("movement_type", "quantity"),
    [("IN", 0), ("OUT", 0), ("IN", -1), ("ADJUST", -1)],
)
def test_invalid_quantities(
    client: TestClient, movement_type: str, quantity: int
) -> None:
    product = make_product(client)

    response = move(client, product["id"], movement_type, quantity)

    assert response.status_code == 422


def test_invalid_movement_type(client: TestClient) -> None:
    product = make_product(client)

    assert move(client, product["id"], "BUY", 1).status_code == 422


def test_note_too_long(client: TestClient) -> None:
    product = make_product(client)

    response = move(client, product["id"], "IN", 1, note="x" * 501)

    assert response.status_code == 422


def test_empty_note_becomes_none(client: TestClient) -> None:
    product = make_product(client)

    response = move(client, product["id"], "IN", 1, note="   ")

    assert response.status_code == 201
    assert response.json()["note"] is None


def test_opening_stock_creates_no_movement(client: TestClient) -> None:
    product = make_product(client, quantity=11)

    assert history(client, product["id"])["total"] == 0


def test_movement_product_not_found(client: TestClient) -> None:
    assert move(client, 999, "IN", 1).status_code == 404


def test_list_movements_filters_paginates_and_sorts(client: TestClient) -> None:
    first = make_product(client, sku="MOV-A")
    second = make_product(client, sku="MOV-B")
    assert move(client, first["id"], "IN", 2).status_code == 201
    assert move(client, first["id"], "OUT", 1).status_code == 201
    assert move(client, second["id"], "IN", 5).status_code == 201

    assert history(client, first["id"])["total"] == 2
    assert history(client, second["id"])["total"] == 1
    assert client.get("/api/movements", params={"movement_type": "IN"}).json()[
        "total"
    ] == 2
    both = client.get(
        "/api/movements",
        params={"product_id": first["id"], "movement_type": "IN"},
    ).json()
    assert both["total"] == 1
    assert both["items"][0]["quantity"] == 2

    page = client.get("/api/movements", params={"page": 2, "page_size": 1}).json()
    assert (page["total"], page["pages"], page["page"], len(page["items"])) == (
        3,
        3,
        2,
        1,
    )

    ascending = client.get("/api/movements", params={"sort": "quantity"}).json()
    descending = client.get("/api/movements", params={"sort": "-quantity"}).json()
    assert [item["quantity"] for item in ascending["items"]] == [1, 2, 5]
    assert [item["quantity"] for item in descending["items"]] == [5, 2, 1]
    assert client.get("/api/movements", params={"sort": "created_atx"}).status_code == 422


def test_product_movements_endpoint(client: TestClient) -> None:
    product = make_product(client)
    assert move(client, product["id"], "IN", 3).status_code == 201

    response = client.get(f"/api/products/{product['id']}/movements")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["product_id"] == product["id"]
    assert client.get("/api/products/999/movements").status_code == 404


def test_product_delete_guard(client: TestClient) -> None:
    with_history = make_product(client, sku="DEL-1")
    assert move(client, with_history["id"], "IN", 1).status_code == 201
    without_history = make_product(client, sku="DEL-2")

    conflict = client.delete(f"/api/products/{with_history['id']}")

    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "Product has stock movements and cannot be deleted"
    assert client.get(f"/api/products/{with_history['id']}").status_code == 200
    assert client.delete(f"/api/products/{without_history['id']}").status_code == 204


def test_movements_are_immutable(client: TestClient) -> None:
    product = make_product(client)
    created = move(client, product["id"], "IN", 1).json()

    # No PATCH/DELETE route exists: FastAPI returns 404 (no matching route/method).
    patch_response = client.patch(
        f"/api/products/{product['id']}/movements/{created['id']}",
        json={"quantity": 99},
    )
    delete_response = client.delete(
        f"/api/products/{product['id']}/movements/{created['id']}"
    )
    assert patch_response.status_code in (404, 405)
    assert delete_response.status_code in (404, 405)
