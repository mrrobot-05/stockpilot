from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from alembic import command
from app.models import Category, Product, Supplier

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
    finally:
        engine.dispose()
