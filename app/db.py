from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine

from app.settings import settings


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    
    # Dynamically alter intake table to add new columns if they do not exist
    if settings.DATABASE_URL.startswith("sqlite"):
        import sqlite3
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
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
                cursor.execute(f"ALTER TABLE intake ADD COLUMN {col} {col_type}")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

        # Alter user table for is_suspended
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN is_suspended BOOLEAN DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Alter consultationsession table for payout_processed
        try:
            cursor.execute("ALTER TABLE consultationsession ADD COLUMN payout_processed BOOLEAN DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Alter childastroorder table for pdf_path
        try:
            cursor.execute("ALTER TABLE childastroorder ADD COLUMN pdf_path VARCHAR")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        conn.close()


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


