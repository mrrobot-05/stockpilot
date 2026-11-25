import json

from fastapi.testclient import TestClient


def form_data(name: str, **overrides: str) -> dict[str, str]:
    data = {
        "name": name,
        "contact_name": "",
        "email": "",
        "phone": "",
        "address": "",
        "notes": "",
    }
    data.update(overrides)
    return data


def setup_suppliers(client: TestClient) -> tuple[dict, dict]:
    acme = client.post(
        "/api/suppliers",
        json={
            "name": "Acme Supply",
            "contact_name": "Jane Doe",
            "email": "jane@acme.example",
        },
    ).json()
    globex = client.post("/api/suppliers", json={"name": "Globex"}).json()
    product = client.post(
        "/api/products",
        json={"sku": "SUP-1", "name": "Widget", "supplier_id": acme["id"]},
    )
    assert product.status_code == 201, product.text
    return acme, globex


def test_suppliers_list_renders_and_search(client: TestClient) -> None:
    acme, _ = setup_suppliers(client)

    response = client.get("/suppliers")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Suppliers",
        "Supplier list",
        "Acme Supply",
        "Globex",
        "Jane Doe",
        'id="supplier-table"',
        'hx-get="/suppliers/new"',
        'id="modal-root"',
        'class="nav-link active"\n          href="/suppliers"',
        f'hx-get="/suppliers/{acme["id"]}/edit"',
    ):
        assert needle in html, needle

    search = client.get("/suppliers", params={"q": "JANE@ACME"})
    assert search.status_code == 200
    assert "Acme Supply" in search.text
    assert "Globex" not in search.text


def test_hx_request_returns_supplier_partial(client: TestClient) -> None:
    setup_suppliers(client)

    response = client.get(
        "/suppliers", params={"q": "Globex"}, headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    assert '<div id="supplier-table"' in response.text
    assert "Globex" in response.text
    assert "Acme Supply" not in response.text
    assert "<!doctype html>" not in response.text.lower()
    assert "StockPilot" not in response.text


def test_supplier_create_updates_table(client: TestClient) -> None:
    response = client.post(
        "/suppliers",
        data=form_data("Initech", contact_name="Alice", email="alice@initech.example"),
    )

    assert response.status_code == 200
    assert "Initech" in response.text
    assert response.headers["hx-retarget"] == "#supplier-table"
    assert response.headers["hx-reswap"] == "outerHTML"
    trigger = json.loads(response.headers["hx-trigger"])
    assert "closeModal" in trigger
    assert trigger["showToast"]["type"] == "success"
    body = client.get("/api/suppliers").json()
    assert body[0]["name"] == "Initech"
    assert body[0]["contact_name"] == "Alice"


def test_duplicate_supplier_name_renders_error(client: TestClient) -> None:
    setup_suppliers(client)

    response = client.post("/suppliers", data=form_data("ACME SUPPLY"))

    assert response.status_code == 200
    assert "A supplier with this name already exists" in response.text
    assert 'id="supplierFormModal"' in response.text
    assert 'id="supplier-table"' not in response.text
    assert len(client.get("/api/suppliers").json()) == 2


def test_supplier_edit_updates_table(client: TestClient) -> None:
    acme, _ = setup_suppliers(client)
    supplier_id = acme["id"]

    modal = client.get(f"/suppliers/{supplier_id}/edit")
    assert modal.status_code == 200
    assert 'id="supplierFormModal"' in modal.text
    assert "jane@acme.example" in modal.text

    response = client.post(
        f"/suppliers/{supplier_id}/edit",
        data=form_data("Acme Renamed", contact_name="Janet", phone="555-0199"),
    )

    assert response.status_code == 200
    assert "Acme Renamed" in response.text
    assert response.headers["hx-retarget"] == "#supplier-table"
    body = client.get(f"/api/suppliers/{supplier_id}").json()
    assert body["name"] == "Acme Renamed"
    assert body["contact_name"] == "Janet"
    assert body["phone"] == "555-0199"


def test_supplier_delete_clears_product_reference(client: TestClient) -> None:
    acme, _ = setup_suppliers(client)
    product = client.get("/api/products", params={"q": "SUP-1"}).json()["items"][0]
    supplier_id = acme["id"]

    modal = client.get(f"/suppliers/{supplier_id}/delete")
    assert modal.status_code == 200
    assert 'id="supplierDeleteModal"' in modal.text
    assert "1 product" in modal.text

    response = client.post(f"/suppliers/{supplier_id}/delete")

    assert response.status_code == 200
    assert "Acme Supply" not in response.text
    assert response.headers["hx-retarget"] == "#supplier-table"
    assert client.get(f"/api/suppliers/{supplier_id}").status_code == 404
    remaining = client.get(f"/api/products/{product['id']}").json()
    assert remaining["supplier_id"] is None
    assert remaining["supplier"] is None


def test_supplier_modals_404(client: TestClient) -> None:
    for path in ("/suppliers/999/edit", "/suppliers/999/delete"):
        response = client.get(path)
        assert response.status_code == 404
        assert "Supplier not found" in response.text


def test_suppliers_ui_has_no_legacy_branding(client: TestClient) -> None:
    acme, _ = setup_suppliers(client)
    legacy_brand = "tel" + "usko"
    supplier_id = acme["id"]

    paths = (
        "/suppliers",
        "/suppliers/new",
        f"/suppliers/{supplier_id}/edit",
        f"/suppliers/{supplier_id}/delete",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert legacy_brand not in response.text.lower()

    partial = client.get("/suppliers", headers={"HX-Request": "true"}).text
    assert legacy_brand not in partial.lower()
