"""Server-rendered HTML pages for the StockPilot UI."""

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.session import get_db
from app.services import categories as category_service
from app.services import movements as movement_service
from app.services import products as product_service
from app.services import stats as stats_service
from app.services import suppliers as supplier_service

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

router = APIRouter(include_in_schema=False)


def money(value: object) -> str:
    """Format a number as USD, e.g. 1234.5 -> '$1,234.50'."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal(0)
    return f"${amount:,.2f}"


def dt(value: object) -> str:
    """Format a datetime (or ISO timestamp) as 'Nov 26, 2026 14:05'."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return str(value)
    return parsed.strftime("%b %d, %Y %H:%M")


templates.env.filters["money"] = money
templates.env.filters["dt"] = dt


def _optional_int(value: str | None) -> int | None:
    """Treat an empty select value as 'no filter' instead of a validation error."""
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _optional_bool(value: str | None) -> bool | None:
    if value is None or not value.strip():
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _products_url(
    q: str = "",
    category_id: int | None = None,
    supplier_id: int | None = None,
    is_active: bool | None = None,
    low_stock: bool = False,
    sort: str = "id",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Build a /products URL that preserves the current filters."""
    params: list[tuple[str, str]] = []
    if q:
        params.append(("q", q))
    if category_id is not None:
        params.append(("category_id", str(category_id)))
    if supplier_id is not None:
        params.append(("supplier_id", str(supplier_id)))
    if is_active is not None:
        params.append(("is_active", "true" if is_active else "false"))
    if low_stock:
        params.append(("low_stock", "true"))
    params.append(("sort", sort))
    if page != 1:
        params.append(("page", str(page)))
    if page_size != 20:
        params.append(("page_size", str(page_size)))
    return "/products?" + urlencode(params)


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)


@router.get("/dashboard", include_in_schema=False)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    stats = stats_service.get_stats(db)
    low_stock, _ = product_service.list_products(
        db, low_stock=True, sort="quantity", page_size=5
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page_title": "Dashboard",
            "stats": stats,
            "low_stock": low_stock,
            "in_stock": max(
                stats.total_products - stats.low_stock_count - stats.out_of_stock_count,
                0,
            ),
        },
    )


@router.get("/products", response_class=HTMLResponse, include_in_schema=False)
def products_page(
    request: Request,
    q: str | None = None,
    category_id: str | None = None,
    supplier_id: str | None = None,
    is_active: str | None = None,
    low_stock: bool = False,
    sort: str = "id",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    category_filter = _optional_int(category_id)
    supplier_filter = _optional_int(supplier_id)
    active_filter = _optional_bool(is_active)
    sort_key = sort if sort.lstrip("-") in product_service.SORT_FIELDS else "id"

    items, total = product_service.list_products(
        db,
        q=(q or "").strip() or None,
        low_stock=low_stock,
        sort=sort_key,
        page=page,
        page_size=page_size,
        category_id=category_filter,
        supplier_id=supplier_filter,
        is_active=active_filter,
    )
    categories = [row[0] for row in category_service.list_categories(db)]
    suppliers = [row[0] for row in supplier_service.list_suppliers(db)]

    context = {
        "page_title": "Products",
        "products": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
        "q": (q or "").strip(),
        "category_id": category_filter,
        "supplier_id": supplier_filter,
        "is_active": active_filter,
        "low_stock": low_stock,
        "sort": sort_key,
        "categories": categories,
        "suppliers": suppliers,
        "url": partial(
            _products_url,
            q=(q or "").strip(),
            category_id=category_filter,
            supplier_id=supplier_filter,
            is_active=active_filter,
            low_stock=low_stock,
            sort=sort_key,
            page_size=page_size,
        ),
    }
    template = (
        "partials/_product_table.html"
        if request.headers.get("hx-request", "").lower() == "true"
        else "products.html"
    )
    return templates.TemplateResponse(request, template, context)


@router.get("/products/{product_id}", response_class=HTMLResponse, include_in_schema=False)
def product_detail_page(
    request: Request, product_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        product = product_service.get_product(db, product_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {
                "page_title": "Product not found",
                "message": "That product does not exist or has been removed.",
            },
            status_code=404,
        )

    movements, total = movement_service.list_product_movements(
        db, product_id, page=1, page_size=20
    )
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {
            "page_title": product.name,
            "product": product,
            "movements": movements,
            "movement_total": total,
        },
    )


def _placeholder_page(title: str, icon: str) -> Callable[..., HTMLResponse]:
    def page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "placeholder.html",
            {"page_title": title, "page_icon": icon},
        )

    return page


PLACEHOLDERS: tuple[tuple[str, str, str], ...] = (
    ("/movements", "Movements", "bi-arrow-left-right"),
    ("/categories", "Categories", "bi-tags"),
    ("/suppliers", "Suppliers", "bi-truck"),
    ("/settings", "Settings", "bi-gear"),
)

for _path, _title, _icon in PLACEHOLDERS:
    router.add_api_route(
        _path,
        _placeholder_page(_title, _icon),
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name=f"page_{_path.strip('/')}",
    )
