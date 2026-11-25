import json

from fastapi.testclient import TestClient


def movement_form_data(
    product_id: int,
    movement_type: str = "IN",
    quantity: int | str = 1,
    note: str = "",
    next: str = "",
) -> dict[str, str]:
    return {
        "product_id": str(product_id),
        "movement_type": movement_type,
        "quantity": str(quantity),
        "note": note,
        "next": next,
    }


def setup_movements(client: TestClient) -> tuple[dict, dict]:
    product_a = client.post(
        "/api/products", json={"sku": "MV-A", "name": "Widget A", "quantity": 20}
    ).json()
    product_b = client.post(
        "/api/products", json={"sku": "MV-B", "name": "Widget B", "quantity": 20}
    ).json()

    specs = (
        (product_a["id"], "IN", 5, "restock A"),
        (product_a["id"], "OUT", 2, "sale A"),
        (product_b["id"], "OUT", 3, "sale B"),
        (product_b["id"], "ADJUST", 10, "stocktake B"),
    )
    for product_id, movement_type, quantity, note in specs:
        response = client.post(
            f"/api/products/{product_id}/movements",
            json={
                "movement_type": movement_type,
                "quantity": quantity,
                "note": note,
            },
        )
        assert response.status_code == 201, response.text
    return product_a, product_b


def test_movements_list_renders(client: TestClient) -> None:
    setup_movements(client)

    response = client.get("/movements")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Movements",
        "Widget A",
        "MV-A",
        "Widget B",
        "MV-B",
        "IN",
        "OUT",
        "ADJUST",
        "sale A",
        "stocktake B",
        'id="movement-table"',
        'hx-target="#movement-table"',
        'hx-get="/movements/new"',
        'id="modal-root"',
        'class="nav-link active"\n          href="/movements"',
    ):
        assert needle in html, needle


def test_movements_filters(client: TestClient) -> None:
    product_a, product_b = setup_movements(client)

    by_product = client.get(
        "/movements", params={"product_id": product_a["id"]}
    ).text
    assert "sale A" in by_product
    assert "restock A" in by_product
    assert "sale B" not in by_product

    other_product = client.get(
        "/movements", params={"product_id": product_b["id"]}
    ).text
    assert "sale B" in other_product
    assert "sale A" not in other_product

    by_type = client.get("/movements", params={"movement_type": "OUT"}).text
    assert "sale A" in by_type
    assert "sale B" in by_type
    assert "restock A" not in by_type
    assert "stocktake B" not in by_type

    combined = client.get(
        "/movements",
        params={"product_id": product_a["id"], "movement_type": "IN"},
    ).text
    assert "restock A" in combined
    assert "sale A" not in combined

    for params in (
        {"product_id": "", "movement_type": ""},
        {"movement_type": "bogus"},
    ):
        response = client.get("/movements", params=params)
        assert response.status_code == 200
        assert "sale A" in response.text


def test_hx_request_returns_movement_partial(client: TestClient) -> None:
    setup_movements(client)

    response = client.get(
        "/movements",
        params={"movement_type": "OUT"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    html = response.text
    assert '<div id="movement-table"' in html
    assert "sale A" in html
    assert "restock A" not in html
    assert "<!doctype html>" not in html.lower()
    assert "StockPilot" not in html


def test_movements_pagination(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-PAGE", "name": "Paged Widget", "quantity": 50}
    ).json()
    for index in range(21):
        response = client.post(
            f"/api/products/{product['id']}/movements",
            json={"movement_type": "OUT", "quantity": 1, "note": f"sale {index}"},
        )
        assert response.status_code == 201, response.text

    first = client.get("/movements").text
    assert "Page 1 of 2" in first
    assert "sale 20" in first  # newest first
    assert "sale 0" not in first  # oldest row falls on page 2

    second = client.get("/movements", params={"page": 2}).text
    assert "Page 2 of 2" in second
    assert "sale 0" in second

    filtered = client.get(
        "/movements", params={"product_id": product["id"], "page": 2}
    ).text
    assert "product_id=" + str(product["id"]) in filtered
    assert "sale 0" in filtered


def test_product_nav_stays_active_on_detail(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-NAV", "name": "Nav Widget"}
    ).json()

    html = client.get(f"/products/{product['id']}").text

    assert 'class="nav-link active"\n          href="/products"' in html
    assert 'class="nav-link active"\n          href="/movements"' not in html


def test_record_movement_modal_renders(client: TestClient) -> None:
    setup_movements(client)

    response = client.get("/movements/new")

    assert response.status_code == 200
    html = response.text
    for needle in (
        'id="movementModal"',
        'name="product_id"',
        'name="movement_type"',
        'name="quantity"',
        'name="note"',
        'name="next"',
        "MV-A",
        "IN",
        "OUT",
        "ADJUST",
    ):
        assert needle in html, needle


def test_record_movement_buttons(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-BTN", "name": "Button Widget"}
    ).json()
    product_id = product["id"]

    list_html = client.get("/movements").text
    detail_html = client.get(f"/products/{product_id}").text

    assert 'hx-get="/movements/new"' in list_html
    assert 'id="modal-root"' in list_html
    assert (
        f'hx-get="/movements/new?product_id={product_id}&amp;next=/products/{product_id}"'
        in detail_html
    )


def test_in_movement_updates_quantity(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-IN", "name": "In Widget", "quantity": 10}
    ).json()

    response = client.post(
        "/movements",
        data=movement_form_data(product["id"], "IN", 5, "supplier restock"),
    )

    assert response.status_code == 200
    assert 'id="movement-table"' in response.text
    assert "supplier restock" in response.text
    assert response.headers["hx-retarget"] == "#movement-table"
    assert response.headers["hx-reswap"] == "outerHTML"
    trigger = json.loads(response.headers["hx-trigger"])
    assert "closeModal" in trigger
    assert trigger["showToast"]["type"] == "success"
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 15


def test_out_movement_updates_quantity(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-OUT", "name": "Out Widget", "quantity": 10}
    ).json()

    response = client.post(
        "/movements",
        data=movement_form_data(product["id"], "OUT", 4, "customer order"),
    )

    assert response.status_code == 200
    assert "customer order" in response.text
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 6


def test_adjust_movement_updates_quantity(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-ADJ", "name": "Adjust Widget", "quantity": 10}
    ).json()

    response = client.post(
        "/movements",
        data=movement_form_data(product["id"], "ADJUST", 3, "stocktake"),
    )

    assert response.status_code == 200
    assert "stocktake" in response.text
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 3


def test_insufficient_stock_shows_form_error(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-LOW", "name": "Low Widget", "quantity": 2}
    ).json()

    response = client.post(
        "/movements", data=movement_form_data(product["id"], "OUT", 5)
    )

    assert response.status_code == 200
    assert "Insufficient stock" in response.text
    assert 'id="movementModal"' in response.text
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 2


def test_movement_validation_shows_form_error(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-VAL", "name": "Valid Widget", "quantity": 10}
    ).json()

    response = client.post(
        "/movements", data=movement_form_data(product["id"], "IN", 0)
    )

    assert response.status_code == 200
    assert "IN and OUT movements require quantity" in response.text
    assert 'id="movementModal"' in response.text
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 10


def test_movement_from_detail_redirects_back(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "MV-REDIR", "name": "Redirect Widget", "quantity": 10}
    ).json()
    expected = f"/products/{product['id']}"

    response = client.post(
        "/movements",
        data=movement_form_data(product["id"], "IN", 2, "from detail", next=expected),
    )

    assert response.status_code == 200
    assert response.headers["hx-redirect"] == expected
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 12


def test_movements_ui_has_no_legacy_branding(client: TestClient) -> None:
    setup_movements(client)
    legacy_brand = "tel" + "usko"

    for path in ("/movements", "/movements/new"):
        response = client.get(path)
        assert response.status_code == 200
        assert legacy_brand not in response.text.lower()

    partial = client.get("/movements", headers={"HX-Request": "true"}).text
    assert legacy_brand not in partial.lower()
