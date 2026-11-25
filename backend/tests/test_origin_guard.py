from fastapi.testclient import TestClient


def local_origin(client: TestClient) -> str:
    return str(client.base_url).rstrip("/")


def product_payload(sku: str = "ORIGIN-1") -> dict[str, str]:
    return {"sku": sku, "name": "Widget"}


def test_cross_origin_post_is_blocked(client: TestClient) -> None:
    response = client.post(
        "/products",
        headers={"Origin": "https://evil.example"},
        data={"sku": "EVIL", "name": "Injected"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin request blocked"
    assert client.get("/api/products").json()["total"] == 0


def test_cross_origin_referer_is_blocked(client: TestClient) -> None:
    response = client.post(
        "/api/products",
        headers={"Referer": "https://evil.example/form"},
        json=product_payload(),
    )

    assert response.status_code == 403
    assert client.get("/api/products").json()["total"] == 0


def test_same_origin_post_is_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/products",
        headers={"Origin": local_origin(client)},
        json=product_payload(),
    )

    assert response.status_code == 201, response.text
    assert response.json()["sku"] == "ORIGIN-1"


def test_same_origin_referer_is_allowed(client: TestClient) -> None:
    referer = f"{local_origin(client)}/products/new"
    response = client.post(
        "/api/categories",
        headers={"Referer": referer},
        json={"name": "Tools"},
    )

    assert response.status_code == 201, response.text


def test_missing_origin_is_allowed(client: TestClient) -> None:
    response = client.post("/api/products", json=product_payload())

    assert response.status_code == 201, response.text


def test_safe_methods_ignore_origin(client: TestClient) -> None:
    response = client.get(
        "/api/products", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 200


def test_other_state_changing_methods_are_blocked(client: TestClient) -> None:
    product = client.post("/api/products", json=product_payload()).json()
    headers = {"Origin": "https://evil.example"}
    product_path = f"/api/products/{product['id']}"

    assert client.patch(product_path, headers=headers, json={"name": "X"}).status_code == 403
    assert client.delete(product_path, headers=headers).status_code == 403
    assert client.get(product_path).json()["name"] == "Widget"
