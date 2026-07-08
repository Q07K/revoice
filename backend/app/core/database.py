from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine(database_url: str) -> Engine:
    connect_args: dict[str, bool] = {}
    if database_url.startswith("sqlite"):
        # Background job threads share the SQLite file with request threads.
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


engine: Engine = _build_engine(get_settings().database_url)
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after a table already exists, which create_all cannot add.
_SQLITE_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("training_jobs", "eta_seconds", "FLOAT"),
    ("cover_jobs", "eta_seconds", "FLOAT"),
    ("cover_jobs", "vocal_gain", "FLOAT DEFAULT 1.5"),
]


def ensure_schema(bind: Engine) -> None:
    """Dev-grade migration for SQLite: add missing columns to existing tables."""
    if not bind.url.get_backend_name().startswith("sqlite"):
        return
    with bind.connect() as connection:
        for table, column, column_type in _SQLITE_COLUMN_MIGRATIONS:
            rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing = {row[1] for row in rows}
            if rows and column not in existing:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                )
                connection.commit()
