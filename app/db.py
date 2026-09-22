from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine

from app.settings import settings


import os
import shutil

db_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""
if not db_url:
    db_url = "sqlite:///./app.db"

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if db_url.startswith("sqlite"):
    # On read-only filesystems (e.g. Vercel serverless), fallback to /tmp/app.db and pre-copy seeded app.db
    is_vercel = os.environ.get("VERCEL") == "1" or "/var/task" in os.path.abspath(__file__)
    if is_vercel or not os.access('.', os.W_OK):
        tmp_db_path = "/tmp/app.db"
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_this_dir)
        _source_db = os.path.join(_project_root, "app.db")
        if os.path.exists(_source_db):
            try:
                if not os.path.exists(tmp_db_path) or os.path.getsize(tmp_db_path) == 0:
                    with open(_source_db, "rb") as src, open(tmp_db_path, "wb") as dst:
                        dst.write(src.read())
                    print(f"Copied seeded app.db from {_source_db} to {tmp_db_path}", flush=True)
            except Exception as _copy_err:
                print(f"Could not copy app.db: {_copy_err}", flush=True)
        db_url = f"sqlite:///{tmp_db_path}"


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

        # Alter astrologer table for Razorpay & Bank Details
        for col in ["razorpay_account_id", "account_holder_name", "bank_account_number", "ifsc_code", "pan_number"]:
            try:
                conn.execute(text(f"ALTER TABLE astrologer ADD COLUMN {col} VARCHAR"))
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


