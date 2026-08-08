from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine

from app.settings import settings


db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    
    # Dynamically alter tables to add new columns if they do not exist (compatible with SQLite and PostgreSQL)
    from sqlalchemy import text
    with engine.begin() as conn:
        for col, col_type in [
            ("full_name", "VARCHAR"),
            ("date_of_birth", "DATE"),
            ("day_of_birth", "VARCHAR"),
            ("birth_time", "VARCHAR"),
            ("birth_place", "VARCHAR"),
            ("current_address", "VARCHAR"),
            ("current_location", "VARCHAR"),
            ("problem", "VARCHAR"),
            ("preferred_system", "VARCHAR")
        ]:
            try:
                conn.execute(text(f"ALTER TABLE intake ADD COLUMN {col} {col_type}"))
            except Exception:
                # Column already exists or table does not exist yet
                pass

        # Alter user table for is_suspended
        try:
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN is_suspended BOOLEAN DEFAULT FALSE"))
        except Exception:
            pass

        # Alter consultationsession table for payout_processed
        try:
            conn.execute(text("ALTER TABLE consultationsession ADD COLUMN payout_processed BOOLEAN DEFAULT FALSE"))
        except Exception:
            pass

        # Alter childastroorder table for pdf_path
        try:
            conn.execute(text("ALTER TABLE childastroorder ADD COLUMN pdf_path VARCHAR"))
        except Exception:
            pass


def get_session():
    with Session(engine) as session:
        yield session


def get_config(session: Session, key: str, default: str) -> str:
    from app.models import SystemConfig
    cfg = session.get(SystemConfig, key)
    if not cfg:
        cfg = SystemConfig(key=key, value=default)
        session.add(cfg)
        session.commit()
    return cfg.value


def set_config(session: Session, key: str, value: str) -> None:
    from app.models import SystemConfig
    cfg = session.get(SystemConfig, key)
    if cfg:
        cfg.value = value
    else:
        cfg = SystemConfig(key=key, value=value)
    session.add(cfg)
    session.commit()


