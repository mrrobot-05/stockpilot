"""Server-rendered HTML pages for the StockPilot UI."""

import json
import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.session import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate
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


DEFAULT_FORM_VALUES: dict[str, object] = {
    "sku": "",
    "name": "",
    "description": "",
    "category_id": None,
    "supplier_id": None,
    "cost_price": "0.00",
    "sell_price": "0.00",
    "quantity": 0,
    "reorder_level": 0,
    "is_active": True,
}


def _form_values_from_product(product: Product) -> dict[str, object]:
    """Prefill an edit modal from an ORM product."""
    return {
        "sku": product.sku,
        "name": product.name,
        "description": product.description or "",
        "category_id": product.category_id,
        "supplier_id": product.supplier_id,
        "cost_price": str(product.cost_price),
        "sell_price": str(product.sell_price),
        "quantity": product.quantity,
        "reorder_level": product.reorder_level,
        "is_active": product.is_active,
    }


def product_form(
    sku: str = Form(""),
    name: str = Form(""),
    description: str = Form(""),
    category_id: str = Form(""),
    supplier_id: str = Form(""),
    cost_price: str = Form(""),
    sell_price: str = Form(""),
    quantity: str = Form(""),
    reorder_level: str = Form(""),
    is_active: str = Form(""),
) -> dict[str, str]:
    """Collect the product modal's form fields without going through the JSON API."""
    return {
        "sku": sku,
        "name": name,
        "description": description,
        "category_id": category_id,
        "supplier_id": supplier_id,
        "cost_price": cost_price,
        "sell_price": sell_price,
        "quantity": quantity,
        "reorder_level": reorder_level,
        "is_active": is_active,
    }


def _normalize_form(form: dict[str, str], *, include_quantity: bool) -> dict[str, object]:
    values: dict[str, object] = {
        "sku": form["sku"].strip(),
        "name": form["name"].strip(),
        "description": form["description"].strip() or None,
        "category_id": _optional_int(form["category_id"]),
        "supplier_id": _optional_int(form["supplier_id"]),
        "cost_price": form["cost_price"].strip() or "0",
        "sell_price": form["sell_price"].strip() or "0",
        "reorder_level": form["reorder_level"].strip() or "0",
        "is_active": form["is_active"].strip().lower() in {"1", "on", "true", "yes"},
    }
    if include_quantity:
        values["quantity"] = form["quantity"].strip() or "0"
    return values


def _form_error(exc: ValidationError | HTTPException) -> str:
    """Turn a validation or service error into one readable modal message."""
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    errors = exc.errors()
    if not errors:
        return "Please check the form values and try again."
    first = errors[0]
    field = ".".join(str(part) for part in first["loc"])
    message = str(first["msg"]).removeprefix("Value error, ")
    return f"{field}: {message}" if field else message


def _form_context(
    db: Session,
    values: dict[str, object],
    *,
    product_id: int | None = None,
    error: str | None = None,
) -> dict:
    editing = product_id is not None
    return {
        "values": values,
        "error": error,
        "product_id": product_id,
        "is_edit": editing,
        "modal_title": "Edit product" if editing else "Add product",
        "form_action": f"/products/{product_id}/edit" if editing else "/products",
        "categories": [row[0] for row in category_service.list_categories(db)],
        "suppliers": [row[0] for row in supplier_service.list_suppliers(db)],
    }


def _table_context(
    db: Session,
    *,
    q: str = "",
    category_id: int | None = None,
    supplier_id: int | None = None,
    is_active: bool | None = None,
    low_stock: bool = False,
    sort: str = "id",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    items, total = product_service.list_products(
        db,
        q=q.strip() or None,
        low_stock=low_stock,
        sort=sort,
        page=page,
        page_size=page_size,
        category_id=category_id,
        supplier_id=supplier_id,
        is_active=is_active,
    )
    return {
        "products": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
        "q": q.strip(),
        "category_id": category_id,
        "supplier_id": supplier_id,
        "is_active": is_active,
        "low_stock": low_stock,
        "sort": sort,
        "url": partial(
            _products_url,
            q=q.strip(),
            category_id=category_id,
            supplier_id=supplier_id,
            is_active=is_active,
            low_stock=low_stock,
            sort=sort,
            page_size=page_size,
        ),
    }


def _table_response(request: Request, db: Session, message: str) -> HTMLResponse:
    """Refresh the table after a write and ask HTMX to close the modal and toast."""
    headers = {
        "HX-Retarget": "#product-table",
        "HX-Reswap": "outerHTML",
        "HX-Trigger": json.dumps(
            {
                "closeModal": "",
                "showToast": {"message": message, "type": "success"},
            }
        ),
    }
    return templates.TemplateResponse(
        request,
        "partials/_product_table.html",
        _table_context(db),
        headers=headers,
    )


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

    context = _table_context(
        db,
        q=q or "",
        category_id=category_filter,
        supplier_id=supplier_filter,
        is_active=active_filter,
        low_stock=low_stock,
        sort=sort_key,
        page=page,
        page_size=page_size,
    )
    context["page_title"] = "Products"
    context["categories"] = [row[0] for row in category_service.list_categories(db)]
    context["suppliers"] = [row[0] for row in supplier_service.list_suppliers(db)]

    template = (
        "partials/_product_table.html"
        if request.headers.get("hx-request", "").lower() == "true"
        else "products.html"
    )
    return templates.TemplateResponse(request, template, context)


@router.get("/products/new", response_class=HTMLResponse, include_in_schema=False)
def new_product_modal(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/_product_form.html",
        _form_context(db, DEFAULT_FORM_VALUES.copy()),
    )


@router.post("/products", response_class=HTMLResponse, include_in_schema=False)
def create_product_submit(
    request: Request,
    form: dict[str, str] = Depends(product_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values = _normalize_form(form, include_quantity=True)
    try:
        product = product_service.create_product(db, ProductCreate(**values))
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_product_form.html",
            _form_context(db, values, error=_form_error(exc)),
        )
    return _table_response(request, db, f"{product.name} added.")


@router.get("/products/{product_id}/edit", response_class=HTMLResponse, include_in_schema=False)
def edit_product_modal(
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
            {"page_title": "Product not found", "message": "That product does not exist."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "partials/_product_form.html",
        _form_context(db, _form_values_from_product(product), product_id=product_id),
    )


@router.post("/products/{product_id}/edit", response_class=HTMLResponse, include_in_schema=False)
def edit_product_submit(
    request: Request,
    product_id: int,
    form: dict[str, str] = Depends(product_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values = _normalize_form(form, include_quantity=False)
    if form["quantity"].strip():
        # The edit form has no quantity control; a supplied value is rejected by the schema.
        values["quantity"] = form["quantity"].strip()
    try:
        product_service.update_product(db, product_id, ProductUpdate(**values))
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_product_form.html",
            _form_context(db, values, product_id=product_id, error=_form_error(exc)),
        )
    return _table_response(request, db, "Product updated.")


@router.get(
    "/products/{product_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_product_modal(
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
            {"page_title": "Product not found", "message": "That product does not exist."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "partials/_product_delete.html",
        {"product": product, "product_id": product_id, "error": None},
    )


@router.post(
    "/products/{product_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_product_submit(
    request: Request, product_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        product_service.delete_product(db, product_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return templates.TemplateResponse(
                request,
                "not_found.html",
                {"page_title": "Product not found", "message": "That product does not exist."},
                status_code=404,
            )
        product = product_service.get_product(db, product_id)
        return templates.TemplateResponse(
            request,
            "partials/_product_delete.html",
            {"product": product, "product_id": product_id, "error": _form_error(exc)},
        )
    return _table_response(request, db, "Product deleted.")


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
