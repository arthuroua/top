import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./carimport.db")
ALEMBIC_REVISION_HEAD = "20260423_000002"


def _normalize_database_url(url: str) -> str:
    # Railway/Postgres URLs often omit the SQLAlchemy driver. We explicitly
    # target psycopg3 because the container installs `psycopg[binary]`.
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_database_url(DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def _alembic_config() -> Config:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def _bootstrap_existing_schema() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    command.stamp(_alembic_config(), ALEMBIC_REVISION_HEAD)


def _run_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    has_alembic_version = "alembic_version" in existing_tables

    if has_alembic_version:
        current_revision = get_current_revision()
        if not current_revision:
            _bootstrap_existing_schema()
            return
        command.upgrade(_alembic_config(), "head")
        return

    if existing_tables:
        _bootstrap_existing_schema()
        return

    command.upgrade(_alembic_config(), "head")


def get_current_revision() -> str | None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def init_db() -> None:
    from app import models  # noqa: F401
    from app.repositories.seo_pages import seed_seo_pages

    _run_migrations()
    with SessionLocal() as db:
        seed_seo_pages(db)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
