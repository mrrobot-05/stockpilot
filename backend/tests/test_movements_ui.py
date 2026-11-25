from fastapi.testclient import TestClient


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


def test_movements_ui_has_no_legacy_branding(client: TestClient) -> None:
    setup_movements(client)
    legacy_brand = "tel" + "usko"

    html = client.get("/movements").text
    partial = client.get("/movements", headers={"HX-Request": "true"}).text

    assert legacy_brand not in html.lower()
    assert legacy_brand not in partial.lower()
