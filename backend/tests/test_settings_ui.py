from fastapi.testclient import TestClient


def test_settings_page_renders(client: TestClient) -> None:
    response = client.get("/settings")

    assert response.status_code == 200
    html = response.text
    for needle in (
        "Settings",
        "Appearance",
        "Currency",
        "USD",
        "v0.1.0",
        "Inventory, on autopilot.",
        'href="/docs"',
        'href="/api/export/products.csv"',
        'href="/api/export/movements.csv"',
        "scripts.seed",
        "movement ledger",
        'href="/movements"',
        'class="nav-link active"\n          href="/settings"',
    ):
        assert needle in html, needle


def test_settings_theme_control(client: TestClient) -> None:
    html = client.get("/settings").text

    assert 'id="themeToggle"' in html
    assert "data-theme-toggle" in html
    assert "Toggle theme" in html

    js = client.get("/static/js/app.js").text
    assert "#themeToggle, [data-theme-toggle]" in js


def test_settings_has_no_legacy_branding(client: TestClient) -> None:
    response = client.get("/settings")

    assert response.status_code == 200
    assert ("tel" + "usko") not in response.text.lower()
