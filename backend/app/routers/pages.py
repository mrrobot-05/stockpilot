"""Server-rendered HTML pages for the StockPilot UI."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.session import get_db
from app.services import products as product_service
from app.services import stats as stats_service

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


def _placeholder_page(title: str, icon: str) -> Callable[..., HTMLResponse]:
    def page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "placeholder.html",
            {"page_title": title, "page_icon": icon},
        )

    return page


PLACEHOLDERS: tuple[tuple[str, str, str], ...] = (
    ("/products", "Products", "bi-box-seam"),
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
