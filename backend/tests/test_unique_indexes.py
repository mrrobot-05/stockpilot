from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Category, Product, Supplier


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_direct_sku_insert_is_case_insensitive(db: Session) -> None:
    db.add(Product(sku="ABC", name="First"))
    db.commit()

    db.add(Product(sku="abc", name="Second"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(Product).count() == 1


def test_direct_category_name_insert_is_case_insensitive(db: Session) -> None:
    db.add(Category(name="Category A"))
    db.commit()

    db.add(Category(name="category a"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(Category).count() == 1


def test_direct_supplier_name_insert_is_case_insensitive(db: Session) -> None:
    db.add(Supplier(name="Supplier A"))
    db.commit()

    db.add(Supplier(name="supplier a"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(Supplier).count() == 1
