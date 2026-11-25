import csv
import io

from fastapi.testclient import TestClient

PRODUCT_HEADER = [
    "sku",
    "name",
    "description",
    "category",
    "supplier",
    "cost_price",
    "sell_price",
    "quantity",
    "reorder_level",
    "is_active",
    "created_at",
    "updated_at",
]
MOVEMENT_HEADER = [
    "id",
    "created_at",
    "product_sku",
    "product_name",
    "movement_type",
    "quantity",
    "quantity_change",
    "stock_after",
    "note",
]


def rows(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.text)))


def test_products_csv_empty(client: TestClient) -> None:
    response = client.get("/api/export/products.csv")

    assert response.status_code == 200
    assert rows(response) == [PRODUCT_HEADER]


def test_products_csv_contents(client: TestClient) -> None:
    category = client.post("/api/categories", json={"name": "Electronics"}).json()
    supplier = client.post("/api/suppliers", json={"name": "Acme Supply"}).json()
    created = client.post(
        "/api/products",
        json={
            "sku": "CSV-1",
            "name": "Desk Lamp",
            "description": "Adjustable, matte black",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
            "cost_price": "12.00",
            "sell_price": "25.50",
            "quantity": 9,
            "reorder_level": 4,
        },
    ).json()
    client.post(
        "/api/products",
        json={"sku": "CSV-2", "name": "Old Lamp", "is_active": False},
    )

    response = client.get("/api/export/products.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="products.csv"'
    parsed = rows(response)
    assert parsed[0] == PRODUCT_HEADER
    assert parsed[1][:10] == [
        "CSV-1",
        "Desk Lamp",
        "Adjustable, matte black",
        "Electronics",
        "Acme Supply",
        "12.00",
        "25.50",
        "9",
        "4",
        "true",
    ]
    assert parsed[1][10] == created["created_at"]
    assert parsed[1][11] == created["updated_at"]
    assert parsed[2][0] == "CSV-2"
    assert parsed[2][3] == ""
    assert parsed[2][4] == ""
    assert parsed[2][9] == "false"


def test_csv_formula_cells_are_sanitized(client: TestClient) -> None:
    payload = '=HYPERLINK("http://evil.example","click")'
    client.post(
        "/api/products",
        json={"sku": "CSV-X", "name": payload, "description": "+SUM(1,2)"},
    )
    product = client.get("/api/products", params={"q": "CSV-X"}).json()["items"][0]
    client.post(
        f"/api/products/{product['id']}/movements",
        json={"movement_type": "IN", "quantity": 1, "note": "@SUM(1+1)"},
    )

    products = rows(client.get("/api/export/products.csv"))
    movements = rows(client.get("/api/export/movements.csv"))

    assert products[1][1] == "'" + payload
    assert products[1][2] == "'+SUM(1,2)"
    assert movements[1][8] == "'@SUM(1+1)"

    # Numeric columns stay numeric and usable in spreadsheets.
    assert products[1][7] == "1"  # quantity after the IN movement
    assert movements[1][5] == "1"
    assert movements[1][7] == "1"


def test_movements_csv_empty(client: TestClient) -> None:
    response = client.get("/api/export/movements.csv")

    assert response.status_code == 200
    assert rows(response) == [MOVEMENT_HEADER]


def test_movements_csv_contents(client: TestClient) -> None:
    product = client.post(
        "/api/products", json={"sku": "CSV-M", "name": "Widget", "quantity": 2}
    ).json()
    created = client.post(
        f"/api/products/{product['id']}/movements",
        json={"movement_type": "IN", "quantity": 5, "note": "  delivery  "},
    ).json()
    client.post(
        f"/api/products/{product['id']}/movements",
        json={"movement_type": "OUT", "quantity": 1},
    )

    response = client.get("/api/export/movements.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="movements.csv"'
    parsed = rows(response)
    assert parsed[0] == MOVEMENT_HEADER
    assert parsed[1] == [
        str(created["id"]),
        created["created_at"],
        "CSV-M",
        "Widget",
        "IN",
        "5",
        "5",
        "7",
        "delivery",
    ]
    assert parsed[2][4] == "OUT"
    assert parsed[2][8] == ""
