from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from alembic import command
from app.models import Category, MovementType, Product, StockMovement, Supplier

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def test_initial_migration_creates_full_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "migration.db"
    url = f"sqlite:///{db_path.as_posix()}"

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= {
            "products",
            "categories",
            "suppliers",
            "stock_movements",
        }
        assert len(inspector.get_columns("products")) == 13

        indexes = {index["name"]: index for index in inspector.get_indexes("products")}
        assert bool(indexes["ix_products_sku"]["unique"]) is True
        assert "ix_products_id" not in indexes
        assert "ix_products_category_id" in indexes
        assert "ix_products_supplier_id" in indexes

        foreign_keys = {
            key["constrained_columns"][0]: key
            for key in inspector.get_foreign_keys("products")
        }
        assert foreign_keys["category_id"]["referred_table"] == "categories"
        assert foreign_keys["category_id"]["options"]["ondelete"] == "SET NULL"
        assert foreign_keys["supplier_id"]["referred_table"] == "suppliers"
        assert foreign_keys["supplier_id"]["options"]["ondelete"] == "SET NULL"

        movement_columns = inspector.get_columns("stock_movements")
        assert [column["name"] for column in movement_columns] == [
            "id",
            "product_id",
            "movement_type",
            "quantity",
            "quantity_change",
            "stock_after",
            "note",
            "created_at",
        ]
        movement_indexes = {
            index["name"] for index in inspector.get_indexes("stock_movements")
        }
        assert {
            "ix_stock_movements_product_id",
            "ix_stock_movements_movement_type",
            "ix_stock_movements_created_at",
        } <= movement_indexes
        movement_fks = inspector.get_foreign_keys("stock_movements")
        assert len(movement_fks) == 1
        assert movement_fks[0]["referred_table"] == "products"
        assert movement_fks[0]["constrained_columns"] == ["product_id"]
        assert movement_fks[0]["options"]["ondelete"] == "RESTRICT"

        with Session(engine) as db:
            category = Category(name="Tools")
            supplier = Supplier(name="Acme")
            db.add_all([category, supplier])
            db.flush()
            product = Product(
                sku="MIG-1",
                name="Referenced product",
                category=category,
                supplier=supplier,
            )
            db.add(product)
            db.commit()
            stored = db.get(Product, product.id)
            assert stored is not None
            assert stored.category.name == "Tools"
            assert stored.supplier.name == "Acme"

            movement = StockMovement(
                product=stored,
                movement_type=MovementType.IN,
                quantity=7,
                quantity_change=7,
                stock_after=7,
                note="opening delivery",
            )
            db.add(movement)
            db.commit()
            assert db.get(StockMovement, movement.id).movement_type == MovementType.IN
    finally:
        engine.dispose()
