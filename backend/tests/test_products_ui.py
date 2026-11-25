import json

import pytest
from fastapi.testclient import TestClient


def product_form_data(quantity: str | None = "7", **overrides: str) -> dict[str, str]:
    data = {
        "sku": "FORM-1",
        "name": "Form Product",
        "description": "Created through the modal",
        "category_id": "",
        "supplier_id": "",
        "cost_price": "5.00",
        "sell_price": "10.00",
        "reorder_level": "2",
        "is_active": "on",
    }
    if quantity is not None:
        data["quantity"] = quantity
    data.update(overrides)
    return data


def setup_products(client: TestClient) -> tuple[dict, dict, list[dict]]:
    category = client.post("/api/categories", json={"name": "Electronics"}).json()
    supplier = client.post("/api/suppliers", json={"name": "Acme Supply"}).json()

    specs = [
        ("SKU-A", "Alpha Widget", 20, 5, True, category["id"], supplier["id"]),
        ("SKU-B", "Beta Cable", 3, 5, True, category["id"], None),
        ("SKU-C", "Gamma Inactive", 10, 2, False, None, None),
    ]
    products = []
    for sku, name, quantity, reorder, active, category_id, supplier_id in specs:
        response = client.post(
            "/api/products",
            json={
                "sku": sku,
                "name": name,
                "quantity": quantity,
                "reorder_level": reorder,
                "is_active": active,
                "category_id": category_id,
                "supplier_id": supplier_id,
                "cost_price": "12.50",
                "sell_price": "25.00",
            },
        )
        assert response.status_code == 201, response.text
        products.append(response.json())
    return category, supplier, products


def test_products_list_renders(client: TestClient) -> None:
    setup_products(client)

    response = client.get("/products")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Products",
        "SKU-A",
        "Alpha Widget",
        "Electronics",
        "Acme Supply",
        "$12.50",
        'id="product-table"',
        'hx-target="#product-table"',
        "sp-sort-link",
        'id="modal-root"',
        'hx-get="/products/new"',
        'hx-get="/products/1/edit"',
        'hx-get="/products/1/delete"',
    ):
        assert needle in html, needle


def test_hx_request_returns_table_partial(client: TestClient) -> None:
    setup_products(client)

    response = client.get(
        "/products", params={"q": "Beta"}, headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    html = response.text
    assert '<div id="product-table"' in html
    assert "SKU-B" in html
    assert "SKU-A" not in html
    assert "q=Beta" in html
    assert "<!doctype html>" not in html.lower()
    assert "StockPilot" not in html


def test_products_filters(client: TestClient) -> None:
    category, supplier, _ = setup_products(client)

    search = client.get("/products", params={"q": "Beta"}).text
    assert "SKU-B" in search
    assert "SKU-A" not in search

    by_category = client.get("/products", params={"category_id": category["id"]}).text
    assert "SKU-A" in by_category
    assert "SKU-B" in by_category
    assert "SKU-C" not in by_category

    by_supplier = client.get("/products", params={"supplier_id": supplier["id"]}).text
    assert "SKU-A" in by_supplier
    assert "SKU-B" not in by_supplier

    inactive = client.get("/products", params={"is_active": "false"}).text
    assert "SKU-C" in inactive
    assert "SKU-A" not in inactive

    low_stock = client.get("/products", params={"low_stock": "true"}).text
    assert "SKU-B" in low_stock
    assert "SKU-A" not in low_stock

    empty_selects = client.get(
        "/products", params={"category_id": "", "supplier_id": "", "is_active": ""}
    )
    assert empty_selects.status_code == 200
    assert "SKU-A" in empty_selects.text

    bad_sort = client.get("/products", params={"sort": "nope"})
    assert bad_sort.status_code == 200
    assert "SKU-A" in bad_sort.text


@pytest.mark.parametrize("sort", ["--id", "-"])
def test_malformed_sort_falls_back_to_id(client: TestClient, sort: str) -> None:
    setup_products(client)

    response = client.get("/products", params={"sort": sort})

    assert response.status_code == 200
    for sku in ("SKU-A", "SKU-B", "SKU-C"):
        assert sku in response.text


def test_unknown_is_active_value_shows_all_products(client: TestClient) -> None:
    setup_products(client)

    response = client.get("/products", params={"is_active": "garbage"})

    assert response.status_code == 200
    for sku in ("SKU-A", "SKU-B", "SKU-C"):
        assert sku in response.text


def test_products_sorting_and_pagination(client: TestClient) -> None:
    for index in range(5):
        response = client.post(
            "/api/products",
            json={"sku": f"P{index}", "name": f"Product {index}", "quantity": 10},
        )
        assert response.status_code == 201, response.text

    first = client.get(
        "/products", params={"page": 1, "page_size": 2, "sort": "sku"}
    ).text
    assert "P0" in first
    assert "P1" in first
    assert "P2" not in first
    assert "Page 1 of 3" in first

    second = client.get(
        "/products", params={"page": 2, "page_size": 2, "sort": "sku"}
    ).text
    assert "P2" in second
    assert "P3" in second
    assert "Page 2 of 3" in second

    descending = client.get(
        "/products", params={"page": 1, "page_size": 2, "sort": "-sku"}
    ).text
    assert "P4" in descending
    assert "P0" not in descending


def test_product_detail_renders_movements(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[0]["id"]
    for movement_type, quantity in (("IN", 5), ("OUT", 2)):
        response = client.post(
            f"/api/products/{product_id}/movements",
            json={"movement_type": movement_type, "quantity": quantity},
        )
        assert response.status_code == 201, response.text

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Alpha Widget",
        "SKU-A",
        "Electronics",
        "Acme Supply",
        "Movement history",
        "IN",
        "OUT",
        "$12.50",
        'id="modal-root"',
        f'hx-get="/products/{product_id}/edit"',
        f'hx-get="/products/{product_id}/delete"',
        'hx-get="/products/new"',
    ):
        assert needle in html, needle


def test_product_detail_404(client: TestClient) -> None:
    response = client.get("/products/999999")

    assert response.status_code == 404
    assert '<h2 class="h3 mt-3">Product not found</h2>' in response.text


def test_create_product_from_form_updates_table(client: TestClient) -> None:
    category, supplier, _ = setup_products(client)

    response = client.post(
        "/products",
        data=product_form_data(
            sku="FORM-1",
            name="Form Product",
            category_id=str(category["id"]),
            supplier_id=str(supplier["id"]),
        ),
    )

    assert response.status_code == 200
    assert 'id="product-table"' in response.text
    assert "FORM-1" in response.text
    assert response.headers["hx-retarget"] == "#product-table"
    assert response.headers["hx-reswap"] == "outerHTML"
    trigger = json.loads(response.headers["hx-trigger"])
    assert "closeModal" in trigger
    assert trigger["showToast"]["type"] == "success"

    page = client.get("/api/products", params={"q": "FORM-1"}).json()
    assert page["total"] == 1
    assert page["items"][0]["quantity"] == 7


def test_create_duplicate_sku_renders_modal_error(client: TestClient) -> None:
    setup_products(client)

    response = client.post("/products", data=product_form_data(sku="SKU-A"))

    assert response.status_code == 200
    assert "A product with this SKU already exists" in response.text
    assert 'id="productFormModal"' in response.text
    assert 'id="product-table"' not in response.text
    assert client.get("/api/products").json()["total"] == 3


def test_edit_product_from_form_updates(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[0]["id"]

    modal = client.get(f"/products/{product_id}/edit")
    assert modal.status_code == 200
    assert 'id="productFormModal"' in modal.text
    assert 'name="quantity"' not in modal.text
    assert "Alpha Widget" in modal.text

    response = client.post(
        f"/products/{product_id}/edit",
        data=product_form_data(quantity=None, sku="SKU-A2", name="Alpha Updated"),
    )

    assert response.status_code == 200
    assert "SKU-A2" in response.text
    assert response.headers["hx-retarget"] == "#product-table"
    updated = client.get(f"/api/products/{product_id}").json()
    assert updated["name"] == "Alpha Updated"
    assert updated["quantity"] == 20


def test_edit_form_rejects_quantity(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[0]["id"]

    response = client.post(
        f"/products/{product_id}/edit",
        data=product_form_data(quantity="5", sku="SKU-A"),
    )

    assert response.status_code == 200
    assert "Use the stock movements API to change quantity" in response.text
    assert 'id="productFormModal"' in response.text
    assert client.get(f"/api/products/{product_id}").json()["quantity"] == 20


def test_delete_product_from_confirm_removes(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[2]["id"]

    modal = client.get(f"/products/{product_id}/delete")
    assert modal.status_code == 200
    assert 'id="productDeleteModal"' in modal.text

    response = client.post(f"/products/{product_id}/delete")

    assert response.status_code == 200
    assert "SKU-C" not in response.text
    assert response.headers["hx-retarget"] == "#product-table"
    assert "closeModal" in json.loads(response.headers["hx-trigger"])
    assert client.get(f"/api/products/{product_id}").status_code == 404


def test_delete_with_movements_returns_conflict_in_modal(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[0]["id"]
    movement = client.post(
        f"/api/products/{product_id}/movements",
        json={"movement_type": "OUT", "quantity": 1},
    )
    assert movement.status_code == 201

    response = client.post(f"/products/{product_id}/delete")

    assert response.status_code == 200
    assert "Product has stock movements and cannot be deleted" in response.text
    assert 'id="productDeleteModal"' in response.text
    assert client.get(f"/api/products/{product_id}").status_code == 200


def test_products_ui_has_no_legacy_branding(client: TestClient) -> None:
    _, _, products = setup_products(client)
    product_id = products[0]["id"]
    legacy_brand = "tel" + "usko"

    paths = (
        "/products",
        "/products/new",
        f"/products/{product_id}",
        f"/products/{product_id}/edit",
        f"/products/{product_id}/delete",
        "/products/999999",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code in (200, 404)
        assert legacy_brand not in response.text.lower()
