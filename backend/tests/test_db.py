from sqlalchemy import create_engine


def test_sqlite_foreign_keys_enabled_on_every_engine() -> None:
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        engine.dispose()
