"""Server-rendered HTML pages for the StockPilot UI."""

import json
import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.session import get_db
from app.models import Category, MovementType, Product, Supplier
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    MovementCreate,
    ProductCreate,
    ProductUpdate,
    SupplierCreate,
    SupplierUpdate,
)
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
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None  # unrecognised values mean "no filter" in the UI


def _page_sort(sort: str) -> str:
    """Accept only a known key, optionally with one leading '-'."""
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if descending and field.startswith("-"):
        return "id"
    return sort if field in product_service.SORT_FIELDS else "id"


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


def _optional_movement_type(value: str | None) -> MovementType | None:
    """Accept an empty select value or a case-insensitive movement type."""
    if value is None or not value.strip():
        return None
    try:
        return MovementType(value.strip().upper())
    except ValueError:
        return None


def _movements_url(
    product_id: int | None = None,
    movement_type: MovementType | None = None,
    page: int = 1,
) -> str:
    """Build a /movements URL that preserves the active filters."""
    params: list[tuple[str, str]] = []
    if product_id is not None:
        params.append(("product_id", str(product_id)))
    if movement_type is not None:
        params.append(("movement_type", movement_type.value))
    if page != 1:
        params.append(("page", str(page)))
    return "/movements?" + urlencode(params) if params else "/movements"


def _movement_table_context(
    db: Session,
    *,
    product_id: int | None = None,
    movement_type: MovementType | None = None,
    page: int = 1,
) -> dict:
    page_size = movement_service.DEFAULT_PAGE_SIZE
    items, total = movement_service.list_movements(
        db,
        product_id=product_id,
        movement_type=movement_type,
        page=page,
        page_size=page_size,
    )
    return {
        "movements": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
        "product_id": product_id,
        "movement_type": movement_type,
        "url": partial(
            _movements_url, product_id=product_id, movement_type=movement_type
        ),
    }


DEFAULT_MOVEMENT_FORM_VALUES: dict[str, object] = {
    "product_id": None,
    "movement_type": "IN",
    "quantity": 1,
    "note": "",
    "next": "",
}


def _all_products(db: Session) -> list[Product]:
    return product_service.list_products(db, sort="name", page_size=1000)[0]


def _safe_next(value: str | None) -> str | None:
    """Only allow post-write redirects back to a local product detail page."""
    candidate = (value or "").strip()
    return candidate if re.fullmatch(r"/products/\d+", candidate) else None


def _movement_form_context(
    db: Session, values: dict[str, object], *, error: str | None = None
) -> dict:
    return {
        "values": values,
        "error": error,
        "products": _all_products(db),
        "types": tuple(MovementType),
    }


def movement_form(
    product_id: str = Form(""),
    movement_type: str = Form(""),
    quantity: str = Form(""),
    note: str = Form(""),
    next: str = Form(""),
) -> dict[str, str]:
    """Collect the record-movement modal fields."""
    return {
        "product_id": product_id,
        "movement_type": movement_type,
        "quantity": quantity,
        "note": note,
        "next": next,
    }


DEFAULT_CATEGORY_FORM_VALUES: dict[str, object] = {"name": "", "description": ""}


def _categories_url(q: str = "") -> str:
    return "/categories?" + urlencode({"q": q}) if q.strip() else "/categories"


def _category_table_context(db: Session, *, q: str = "") -> dict:
    rows = category_service.list_categories(db, q=q.strip() or None)
    return {
        "categories": rows,
        "total": len(rows),
        "q": q.strip(),
        "url": partial(_categories_url, q=q.strip()),
    }


def _category_table_response(request: Request, db: Session, message: str) -> HTMLResponse:
    headers = {
        "HX-Retarget": "#category-table",
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
        "partials/_category_table.html",
        _category_table_context(db),
        headers=headers,
    )


def _form_values_from_category(category: Category) -> dict[str, object]:
    return {"name": category.name, "description": category.description or ""}


def _category_form_context(
    values: dict[str, object],
    *,
    category_id: int | None = None,
    error: str | None = None,
) -> dict:
    editing = category_id is not None
    return {
        "values": values,
        "error": error,
        "category_id": category_id,
        "is_edit": editing,
        "modal_title": "Edit category" if editing else "Add category",
        "form_action": (
            f"/categories/{category_id}/edit" if editing else "/categories"
        ),
    }


def category_form(
    name: str = Form(""), description: str = Form("")
) -> dict[str, str]:
    """Collect the category modal fields."""
    return {"name": name, "description": description}


def _category_not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "not_found.html",
        {"page_title": "Category not found", "message": "That category does not exist."},
        status_code=404,
    )


DEFAULT_SUPPLIER_FORM_VALUES: dict[str, object] = {
    "name": "",
    "contact_name": "",
    "email": "",
    "phone": "",
    "address": "",
    "notes": "",
}


def _suppliers_url(q: str = "") -> str:
    return "/suppliers?" + urlencode({"q": q}) if q.strip() else "/suppliers"


def _supplier_table_context(db: Session, *, q: str = "") -> dict:
    rows = supplier_service.list_suppliers(db, q=q.strip() or None)
    return {
        "suppliers": rows,
        "total": len(rows),
        "q": q.strip(),
        "url": partial(_suppliers_url, q=q.strip()),
    }


def _supplier_table_response(request: Request, db: Session, message: str) -> HTMLResponse:
    headers = {
        "HX-Retarget": "#supplier-table",
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
        "partials/_supplier_table.html",
        _supplier_table_context(db),
        headers=headers,
    )


def _form_values_from_supplier(supplier: Supplier) -> dict[str, object]:
    return {
        "name": supplier.name,
        "contact_name": supplier.contact_name or "",
        "email": supplier.email or "",
        "phone": supplier.phone or "",
        "address": supplier.address or "",
        "notes": supplier.notes or "",
    }


def _supplier_form_context(
    values: dict[str, object],
    *,
    supplier_id: int | None = None,
    error: str | None = None,
) -> dict:
    editing = supplier_id is not None
    return {
        "values": values,
        "error": error,
        "supplier_id": supplier_id,
        "is_edit": editing,
        "modal_title": "Edit supplier" if editing else "Add supplier",
        "form_action": f"/suppliers/{supplier_id}/edit" if editing else "/suppliers",
    }


def supplier_form(
    name: str = Form(""),
    contact_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    notes: str = Form(""),
) -> dict[str, str]:
    """Collect the supplier modal fields."""
    return {
        "name": name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "address": address,
        "notes": notes,
    }


def _supplier_not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "not_found.html",
        {"page_title": "Supplier not found", "message": "That supplier does not exist."},
        status_code=404,
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
    out_of_stock, _ = product_service.list_products(
        db, out_of_stock=True, sort="quantity", page_size=5
    )
    attention = sorted(
        {product.id: product for product in [*low_stock, *out_of_stock]}.values(),
        key=lambda product: (product.quantity, product.id),
    )[:5]
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page_title": "Dashboard",
            "stats": stats,
            "attention": attention,
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
    sort_key = _page_sort(sort)

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


@router.get("/movements", response_class=HTMLResponse, include_in_schema=False)
def movements_page(
    request: Request,
    product_id: str | None = None,
    movement_type: str | None = None,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    product_filter = _optional_int(product_id)
    type_filter = _optional_movement_type(movement_type)
    context = _movement_table_context(
        db, product_id=product_filter, movement_type=type_filter, page=page
    )
    context["page_title"] = "Movements"
    context["products"] = _all_products(db)

    template = (
        "partials/_movement_table.html"
        if request.headers.get("hx-request", "").lower() == "true"
        else "movements.html"
    )
    return templates.TemplateResponse(request, template, context)


@router.get("/movements/new", response_class=HTMLResponse, include_in_schema=False)
def new_movement_modal(
    request: Request,
    product_id: str | None = None,
    next: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values = DEFAULT_MOVEMENT_FORM_VALUES.copy()
    values["product_id"] = _optional_int(product_id)
    values["next"] = _safe_next(next) or ""
    return templates.TemplateResponse(
        request, "partials/_movement_form.html", _movement_form_context(db, values)
    )


@router.post("/movements", response_class=HTMLResponse, include_in_schema=False)
def create_movement_submit(
    request: Request,
    form: dict[str, str] = Depends(movement_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values: dict[str, object] = {
        "product_id": _optional_int(form["product_id"]),
        "movement_type": form["movement_type"].strip().upper(),
        "quantity": form["quantity"].strip() or "0",
        "note": form["note"].strip(),
        "next": _safe_next(form["next"]) or "",
    }
    if values["product_id"] is None:
        return templates.TemplateResponse(
            request,
            "partials/_movement_form.html",
            _movement_form_context(db, values, error="product: Choose a product."),
        )

    try:
        payload = MovementCreate(
            movement_type=str(values["movement_type"]),
            quantity=str(values["quantity"]),
            note=str(values["note"]) or None,
        )
        movement = movement_service.create_movement(db, int(values["product_id"]), payload)
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_movement_form.html",
            _movement_form_context(db, values, error=_form_error(exc)),
        )

    if values["next"]:
        return HTMLResponse(content="", headers={"HX-Redirect": str(values["next"])})

    headers = {
        "HX-Retarget": "#movement-table",
        "HX-Reswap": "outerHTML",
        "HX-Trigger": json.dumps(
            {
                "closeModal": "",
                "showToast": {
                    "message": (
                        f"{movement.product.name}: "
                        f"{movement.movement_type.value} movement recorded."
                    ),
                    "type": "success",
                },
            }
        ),
    }
    return templates.TemplateResponse(
        request,
        "partials/_movement_table.html",
        _movement_table_context(db),
        headers=headers,
    )


@router.get("/categories", response_class=HTMLResponse, include_in_schema=False)
def categories_page(
    request: Request, q: str | None = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    context = _category_table_context(db, q=q or "")
    context["page_title"] = "Categories"
    template = (
        "partials/_category_table.html"
        if request.headers.get("hx-request", "").lower() == "true"
        else "categories.html"
    )
    return templates.TemplateResponse(request, template, context)


@router.get("/categories/new", response_class=HTMLResponse, include_in_schema=False)
def new_category_modal(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/_category_form.html",
        _category_form_context(DEFAULT_CATEGORY_FORM_VALUES.copy()),
    )


@router.post("/categories", response_class=HTMLResponse, include_in_schema=False)
def create_category_submit(
    request: Request,
    form: dict[str, str] = Depends(category_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values: dict[str, object] = {
        "name": form["name"].strip(),
        "description": form["description"].strip(),
    }
    try:
        category = category_service.create_category(
            db,
            CategoryCreate(name=str(values["name"]), description=str(values["description"]) or None),
        )
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_category_form.html",
            _category_form_context(values, error=_form_error(exc)),
        )
    return _category_table_response(request, db, f"{category.name} added.")


@router.get(
    "/categories/{category_id}/edit", response_class=HTMLResponse, include_in_schema=False
)
def edit_category_modal(
    request: Request, category_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        category = category_service.get_category(db, category_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return _category_not_found(request)
    return templates.TemplateResponse(
        request,
        "partials/_category_form.html",
        _category_form_context(
            _form_values_from_category(category), category_id=category_id
        ),
    )


@router.post(
    "/categories/{category_id}/edit", response_class=HTMLResponse, include_in_schema=False
)
def edit_category_submit(
    request: Request,
    category_id: int,
    form: dict[str, str] = Depends(category_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values: dict[str, object] = {
        "name": form["name"].strip(),
        "description": form["description"].strip(),
    }
    try:
        category_service.update_category(
            db,
            category_id,
            CategoryUpdate(
                name=str(values["name"]), description=str(values["description"]) or None
            ),
        )
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_category_form.html",
            _category_form_context(
                values, category_id=category_id, error=_form_error(exc)
            ),
        )
    return _category_table_response(request, db, "Category updated.")


@router.get(
    "/categories/{category_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_category_modal(
    request: Request, category_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        category = category_service.get_category(db, category_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return _category_not_found(request)
    count = next(
        (n for item, n in category_service.list_categories(db) if item.id == category_id),
        0,
    )
    return templates.TemplateResponse(
        request,
        "partials/_category_delete.html",
        {"category": category, "category_id": category_id, "product_count": count, "error": None},
    )


@router.post(
    "/categories/{category_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_category_submit(
    request: Request, category_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        category_service.delete_category(db, category_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return _category_not_found(request)
        category = category_service.get_category(db, category_id)
        count = next(
            (n for item, n in category_service.list_categories(db) if item.id == category_id),
            0,
        )
        return templates.TemplateResponse(
            request,
            "partials/_category_delete.html",
            {
                "category": category,
                "category_id": category_id,
                "product_count": count,
                "error": _form_error(exc),
            },
        )
    return _category_table_response(request, db, "Category deleted.")


@router.get("/suppliers", response_class=HTMLResponse, include_in_schema=False)
def suppliers_page(
    request: Request, q: str | None = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    context = _supplier_table_context(db, q=q or "")
    context["page_title"] = "Suppliers"
    template = (
        "partials/_supplier_table.html"
        if request.headers.get("hx-request", "").lower() == "true"
        else "suppliers.html"
    )
    return templates.TemplateResponse(request, template, context)


@router.get("/suppliers/new", response_class=HTMLResponse, include_in_schema=False)
def new_supplier_modal(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/_supplier_form.html",
        _supplier_form_context(DEFAULT_SUPPLIER_FORM_VALUES.copy()),
    )


@router.post("/suppliers", response_class=HTMLResponse, include_in_schema=False)
def create_supplier_submit(
    request: Request,
    form: dict[str, str] = Depends(supplier_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values: dict[str, object] = {key: form[key].strip() for key in form}
    try:
        supplier = supplier_service.create_supplier(db, SupplierCreate(**values))
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_supplier_form.html",
            _supplier_form_context(values, error=_form_error(exc)),
        )
    return _supplier_table_response(request, db, f"{supplier.name} added.")


@router.get(
    "/suppliers/{supplier_id}/edit", response_class=HTMLResponse, include_in_schema=False
)
def edit_supplier_modal(
    request: Request, supplier_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        supplier = supplier_service.get_supplier(db, supplier_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return _supplier_not_found(request)
    return templates.TemplateResponse(
        request,
        "partials/_supplier_form.html",
        _supplier_form_context(
            _form_values_from_supplier(supplier), supplier_id=supplier_id
        ),
    )


@router.post(
    "/suppliers/{supplier_id}/edit", response_class=HTMLResponse, include_in_schema=False
)
def edit_supplier_submit(
    request: Request,
    supplier_id: int,
    form: dict[str, str] = Depends(supplier_form),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    values: dict[str, object] = {key: form[key].strip() for key in form}
    try:
        supplier_service.update_supplier(db, supplier_id, SupplierUpdate(**values))
    except (ValidationError, HTTPException) as exc:
        return templates.TemplateResponse(
            request,
            "partials/_supplier_form.html",
            _supplier_form_context(
                values, supplier_id=supplier_id, error=_form_error(exc)
            ),
        )
    return _supplier_table_response(request, db, "Supplier updated.")


@router.get(
    "/suppliers/{supplier_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_supplier_modal(
    request: Request, supplier_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        supplier = supplier_service.get_supplier(db, supplier_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return _supplier_not_found(request)
    count = next(
        (n for item, n in supplier_service.list_suppliers(db) if item.id == supplier_id),
        0,
    )
    return templates.TemplateResponse(
        request,
        "partials/_supplier_delete.html",
        {"supplier": supplier, "supplier_id": supplier_id, "product_count": count, "error": None},
    )


@router.post(
    "/suppliers/{supplier_id}/delete", response_class=HTMLResponse, include_in_schema=False
)
def delete_supplier_submit(
    request: Request, supplier_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        supplier_service.delete_supplier(db, supplier_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return _supplier_not_found(request)
        supplier = supplier_service.get_supplier(db, supplier_id)
        count = next(
            (n for item, n in supplier_service.list_suppliers(db) if item.id == supplier_id),
            0,
        )
        return templates.TemplateResponse(
            request,
            "partials/_supplier_delete.html",
            {
                "supplier": supplier,
                "supplier_id": supplier_id,
                "product_count": count,
                "error": _form_error(exc),
            },
        )
    return _supplier_table_response(request, db, "Supplier deleted.")


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "settings.html", {"page_title": "Settings"}
    )
