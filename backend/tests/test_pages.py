from fastapi.testclient import TestClient

PAGE_PATHS = (
    "/dashboard",
    "/products",
    "/movements",
    "/categories",
    "/suppliers",
    "/settings",
)

DASHBOARD_LABELS = (
    "StockPilot",
    "Dashboard",
    "Total products",
    "Stock units",
    "Inventory value",
    "Low stock",
)


def test_root_redirects_to_dashboard(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


def test_dashboard_empty_state(client: TestClient) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    for label in DASHBOARD_LABELS:
        assert label in response.text
    assert "scripts.seed" in response.text
    assert "Your inventory is ready for takeoff" in response.text


def test_dashboard_shows_low_stock_product_and_movement(client: TestClient) -> None:
    category = client.post("/api/categories", json={"name": "Electronics"}).json()
    product = client.post(
        "/api/products",
        json={
            "sku": "LOW-42",
            "name": " desk lamp ",
            "quantity": 2,
            "reorder_level": 5,
            "cost_price": "12.50",
            "sell_price": "30.00",
            "category_id": category["id"],
        },
    ).json()
    assert product["sku"] == "LOW-42"

    movement = client.post(
        f"/api/products/{product['id']}/movements",
        json={"movement_type": "OUT", "quantity": 1, "note": "customer order"},
    )
    assert movement.status_code == 201, movement.text

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "LOW-42" in response.text
    assert "desk lamp" in response.text
    assert "OUT" in response.text
    assert "customer order" in response.text
    assert "$12.50" in response.text
    assert "Your inventory is ready for takeoff" not in response.text


def test_static_assets_are_served(client: TestClient) -> None:
    css = client.get("/static/css/app.css")
    js = client.get("/static/js/app.js")

    assert css.status_code == 200
    assert "--sp-" in css.text
    assert js.status_code == 200
    assert "showToast" in js.text
    assert "htmx:beforeRequest" in js.text
    assert "hidden.bs.modal" in js.text


def test_dashboard_attention_merges_low_and_out_of_stock(client: TestClient) -> None:
    for sku, quantity in (("ATT-LOW", 2), ("ATT-ZERO", 0), ("ATT-OK", 50)):
        response = client.post(
            "/api/products",
            json={"sku": sku, "name": sku, "quantity": quantity, "reorder_level": 5},
        )
        assert response.status_code == 201, response.text

    html = client.get("/dashboard").text

    assert "ATT-LOW" in html
    assert "ATT-ZERO" in html
    assert "ATT-OK" not in html
    assert "Low stock" in html
    assert "Out of stock" in html
    assert html.index("ATT-ZERO") < html.index("ATT-LOW")  # out of stock sorts first


def test_pages_have_no_legacy_branding(client: TestClient) -> None:
    for path in PAGE_PATHS:
        response = client.get(path)
        assert response.status_code == 200
        legacy_brand = "tel" + "usko"
        assert legacy_brand not in response.text.lower()


def test_pages_are_excluded_from_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    for path in ("/", *PAGE_PATHS):
        assert path not in paths
