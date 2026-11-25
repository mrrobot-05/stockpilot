import json

from fastapi.testclient import TestClient


def form_data(name: str, description: str = "") -> dict[str, str]:
    return {"name": name, "description": description}


def setup_categories(client: TestClient) -> tuple[dict, dict]:
    tools = client.post(
        "/api/categories", json={"name": "Tools", "description": "hand tools"}
    ).json()
    office = client.post(
        "/api/categories", json={"name": "Office", "description": "stationery"}
    ).json()
    product = client.post(
        "/api/products",
        json={"sku": "CAT-1", "name": "Hammer", "category_id": tools["id"]},
    )
    assert product.status_code == 201, product.text
    return tools, office


def test_categories_list_renders_and_search(client: TestClient) -> None:
    tools, _ = setup_categories(client)

    response = client.get("/categories")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Categories",
        "Category list",
        "Tools",
        "Office",
        "hand tools",
        'id="category-table"',
        'hx-get="/categories/new"',
        'id="modal-root"',
        'class="nav-link active"\n          href="/categories"',
        f'hx-get="/categories/{tools["id"]}/edit"',
    ):
        assert needle in html, needle

    search = client.get("/categories", params={"q": "STATIONERY"})
    assert search.status_code == 200
    assert "Office" in search.text
    assert "Tools" not in search.text


def test_hx_request_returns_category_partial(client: TestClient) -> None:
    setup_categories(client)

    response = client.get(
        "/categories", params={"q": "Tools"}, headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    assert '<div id="category-table"' in response.text
    assert "Tools" in response.text
    assert "Office" not in response.text
    assert "<!doctype html>" not in response.text.lower()
    assert "StockPilot" not in response.text


def test_category_create_updates_table(client: TestClient) -> None:
    response = client.post("/categories", data=form_data("New Category", "fresh group"))

    assert response.status_code == 200
    assert "New Category" in response.text
    assert response.headers["hx-retarget"] == "#category-table"
    assert response.headers["hx-reswap"] == "outerHTML"
    trigger = json.loads(response.headers["hx-trigger"])
    assert "closeModal" in trigger
    assert trigger["showToast"]["type"] == "success"
    assert client.get("/api/categories").json()[0]["name"] == "New Category"


def test_duplicate_category_name_renders_error(client: TestClient) -> None:
    setup_categories(client)

    response = client.post("/categories", data=form_data("TOOLS"))

    assert response.status_code == 200
    assert "A category with this name already exists" in response.text
    assert 'id="categoryFormModal"' in response.text
    assert 'id="category-table"' not in response.text
    assert len(client.get("/api/categories").json()) == 2


def test_category_edit_updates_table(client: TestClient) -> None:
    tools, _ = setup_categories(client)
    category_id = tools["id"]

    modal = client.get(f"/categories/{category_id}/edit")
    assert modal.status_code == 200
    assert 'id="categoryFormModal"' in modal.text
    assert "hand tools" in modal.text

    response = client.post(
        f"/categories/{category_id}/edit", data=form_data("Renamed", "updated description")
    )

    assert response.status_code == 200
    assert "Renamed" in response.text
    assert response.headers["hx-retarget"] == "#category-table"
    body = client.get(f"/api/categories/{category_id}").json()
    assert body["name"] == "Renamed"
    assert body["description"] == "updated description"


def test_category_delete_clears_product_reference(client: TestClient) -> None:
    tools, _ = setup_categories(client)
    product = client.get("/api/products", params={"q": "CAT-1"}).json()["items"][0]
    category_id = tools["id"]

    modal = client.get(f"/categories/{category_id}/delete")
    assert modal.status_code == 200
    assert 'id="categoryDeleteModal"' in modal.text
    assert "1 product" in modal.text

    response = client.post(f"/categories/{category_id}/delete")

    assert response.status_code == 200
    assert "Tools" not in response.text
    assert response.headers["hx-retarget"] == "#category-table"
    assert client.get(f"/api/categories/{category_id}").status_code == 404
    remaining = client.get(f"/api/products/{product['id']}").json()
    assert remaining["category_id"] is None
    assert remaining["category"] is None


def test_category_delete_without_products(client: TestClient) -> None:
    created = client.post("/api/categories", json={"name": "Empty"}).json()

    response = client.post(f"/categories/{created['id']}/delete")

    assert response.status_code == 200
    assert "Empty" not in response.text
    assert client.get(f"/api/categories/{created['id']}").status_code == 404


def test_category_modals_404(client: TestClient) -> None:
    for path in ("/categories/999/edit", "/categories/999/delete"):
        response = client.get(path)
        assert response.status_code == 404
        assert '<h2 class="h3 mt-3">Category not found</h2>' in response.text


def test_categories_ui_has_no_legacy_branding(client: TestClient) -> None:
    tools, _ = setup_categories(client)
    legacy_brand = "tel" + "usko"
    category_id = tools["id"]

    paths = (
        "/categories",
        "/categories/new",
        f"/categories/{category_id}/edit",
        f"/categories/{category_id}/delete",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert legacy_brand not in response.text.lower()

    partial = client.get("/categories", headers={"HX-Request": "true"}).text
    assert legacy_brand not in partial.lower()
