"""Idempotent demo data loader. Run from backend/: python -m scripts.seed."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Category, Product, Supplier
from app.schemas import MovementCreate, ProductCreate
from app.services.movements import create_movement
from app.services.products import create_product
from app.services.stats import get_stats

CATEGORIES = [
    ("Electronics", "Devices, components and accessories"),
    ("Office", "Desk and stationery supplies"),
    ("Furniture", "Office seating and workstations"),
]

SUPPLIERS = [
    (
        "Acme Supply",
        "Jane Doe",
        "jane@acme.example",
        "555-0101",
        "1 Main Street",
        "Preferred vendor for hardware",
    ),
    (
        "Globex",
        "John Smith",
        "john@globex.example",
        "555-0102",
        "22 Market Road",
        "Fast shipping",
    ),
    (
        "Initech",
        "Alice Brown",
        "alice@initech.example",
        "555-0103",
        "9 Industrial Way",
        "Bulk orders",
    ),
]

PRODUCTS = [
    {
        "sku": "LAPTOP-STAND",
        "name": "Laptop Stand",
        "description": "Adjustable aluminium stand",
        "category": "Electronics",
        "supplier": "Acme Supply",
        "cost_price": "18.00",
        "sell_price": "39.99",
        "quantity": 25,
        "reorder_level": 8,
    },
    {
        "sku": "WIRELESS-MOUSE",
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse",
        "category": "Electronics",
        "supplier": "Globex",
        "cost_price": "9.50",
        "sell_price": "24.99",
        "quantity": 20,
        "reorder_level": 10,
    },
    {
        "sku": "USB-C-CABLE",
        "name": "USB-C Cable",
        "description": "2 m braided USB-C cable",
        "category": "Electronics",
        "supplier": "Initech",
        "cost_price": "2.25",
        "sell_price": "8.99",
        "quantity": 12,
        "reorder_level": 15,
    },
    {
        "sku": "NOTEBOOK-A5",
        "name": "Notebook A5",
        "description": "Ruled hardcover notebook",
        "category": "Office",
        "supplier": "Globex",
        "cost_price": "1.80",
        "sell_price": "5.50",
        "quantity": 60,
        "reorder_level": 20,
    },
    {
        "sku": "PENS-12",
        "name": "Ballpoint Pens (12-pack)",
        "description": "Blue ink, medium tip",
        "category": "Office",
        "supplier": "Acme Supply",
        "cost_price": "3.00",
        "sell_price": "9.95",
        "quantity": 40,
        "reorder_level": 15,
    },
    {
        "sku": "DESK-ORGANIZER",
        "name": "Desk Organizer",
        "description": "Bamboo desktop organizer",
        "category": "Office",
        "supplier": "Initech",
        "cost_price": "7.40",
        "sell_price": "18.00",
        "quantity": 15,
        "reorder_level": 6,
    },
    {
        "sku": "ERGONOMIC-CHAIR",
        "name": "Ergonomic Chair",
        "description": "Adjustable task chair",
        "category": "Furniture",
        "supplier": "Globex",
        "cost_price": "85.00",
        "sell_price": "199.00",
        "quantity": 8,
        "reorder_level": 3,
    },
    {
        "sku": "STANDING-DESK",
        "name": "Standing Desk",
        "description": "Height-adjustable desk",
        "category": "Furniture",
        "supplier": "Acme Supply",
        "cost_price": "210.00",
        "sell_price": "449.00",
        "quantity": 5,
        "reorder_level": 2,
    },
]

MOVEMENTS = [
    ("LAPTOP-STAND", "OUT", 5, "Sale to customer"),
    ("WIRELESS-MOUSE", "OUT", 16, "Sale to customer"),
    ("USB-C-CABLE", "OUT", 12, "Sale to customer"),
    ("NOTEBOOK-A5", "OUT", 10, "Office restock order"),
    ("PENS-12", "OUT", 8, "Sale to customer"),
    ("DESK-ORGANIZER", "OUT", 4, "Sale to customer"),
    ("DESK-ORGANIZER", "IN", 10, "Supplier restock"),
    ("ERGONOMIC-CHAIR", "OUT", 2, "Sale to customer"),
    ("ERGONOMIC-CHAIR", "ADJUST", 7, "Stocktake correction"),
    ("STANDING-DESK", "OUT", 1, "Sale to customer"),
]


def _get_or_create_category(db: Session, name: str, description: str) -> Category:
    category = db.scalar(select(Category).where(Category.name == name))
    if category is None:
        category = Category(name=name, description=description)
        db.add(category)
        db.commit()
        db.refresh(category)
    return category


def _get_or_create_supplier(
    db: Session,
    name: str,
    contact_name: str,
    email: str,
    phone: str,
    address: str,
    notes: str,
) -> Supplier:
    supplier = db.scalar(select(Supplier).where(Supplier.name == name))
    if supplier is None:
        supplier = Supplier(
            name=name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            notes=notes,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
    return supplier


def seed() -> None:
    """Populate the database once; skip entirely if any products already exist."""
    db = SessionLocal()
    try:
        existing = db.scalar(select(func.count()).select_from(Product)) or 0
        if existing:
            print(f"Seed skipped: {existing} products already exist.")
            return

        categories = {
            name: _get_or_create_category(db, name, description)
            for name, description in CATEGORIES
        }
        suppliers = {
            name: _get_or_create_supplier(db, name, *contact)
            for name, *contact in SUPPLIERS
        }

        products: dict[str, Product] = {}
        for spec in PRODUCTS:
            product = create_product(
                db,
                ProductCreate(
                    sku=spec["sku"],
                    name=spec["name"],
                    description=spec["description"],
                    category_id=categories[spec["category"]].id,
                    supplier_id=suppliers[spec["supplier"]].id,
                    cost_price=spec["cost_price"],
                    sell_price=spec["sell_price"],
                    quantity=spec["quantity"],
                    reorder_level=spec["reorder_level"],
                ),
            )
            products[spec["sku"]] = product

        movement_count = 0
        for sku, movement_type, quantity, note in MOVEMENTS:
            create_movement(
                db,
                products[sku].id,
                MovementCreate(
                    movement_type=movement_type, quantity=quantity, note=note
                ),
            )
            movement_count += 1

        stats = get_stats(db)
        print(
            f"Seed complete: {stats.category_count} categories, "
            f"{stats.supplier_count} suppliers, {stats.total_products} products, "
            f"{movement_count} movements, {stats.total_stock_units} stock units."
        )
        print(
            f"Low stock: {stats.low_stock_count}; "
            f"out of stock: {stats.out_of_stock_count}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
