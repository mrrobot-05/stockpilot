from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from alembic import command
from app.models import Product

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def test_initial_migration_creates_products_table(tmp_path: Path) -> None:
    db_path = tmp_path / "migration.db"
    url = f"sqlite:///{db_path.as_posix()}"

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert "products" in inspector.get_table_names()
        assert len(inspector.get_columns("products")) == 11

        indexes = {index["name"]: index for index in inspector.get_indexes("products")}
        assert "ix_products_sku" in indexes
        assert bool(indexes["ix_products_sku"]["unique"]) is True
        assert "ix_products_id" not in indexes

        with Session(engine) as db:
            product = Product(sku="MIG-1", name="Migration product")
            db.add(product)
            db.commit()
            assert db.get(Product, product.id) is not None
    finally:
        engine.dispose()
