"""
Adizon - Database Configuration
PostgreSQL Connection & Session Management
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Database URL aus Environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://adizon:adizon_dev_password@localhost:5432/adizon_users")

# SQLAlchemy Engine
# pool_pre_ping=True: Test connection before using (automatic reconnect)
# echo=False: Disable SQL query logging (set True for debugging)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class für Models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency für Database Sessions.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialisiert die Datenbank (erstellt alle Tabellen).
    
    Note: In Production sollten Migrationen via Alembic laufen.
    Diese Funktion ist primär für Tests und Development.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def test_connection() -> bool:
    """
    Testet die Database-Connection.
    
    Returns:
        True wenn Connection erfolgreich, False sonst
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅ PostgreSQL Connection successful: {DATABASE_URL.split('@')[1]}")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL Connection failed: {e}")
        return False


# Event Listener: Log reconnections (optional, für Debugging)
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Wird bei jedem neuen Connection-Pool-Connect aufgerufen"""
    # print(f"🔌 New DB connection established")
    pass


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Wird beim Schließen einer Connection aufgerufen"""
    # print(f"🔌 DB connection closed")
    pass

