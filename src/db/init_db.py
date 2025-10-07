"""Database initialization script"""

from .connection import engine, Base
from .models import Statement, StagingTransaction


def init_database():
    """
    Initialize database by creating all tables.

    This uses SQLAlchemy's create_all() which is safe to run multiple times
    (it only creates tables that don't exist).
    """
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
    print("  - statements")
    print("  - staging_transactions")


if __name__ == "__main__":
    init_database()
