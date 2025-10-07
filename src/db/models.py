"""SQLAlchemy ORM models for database tables"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from .connection import Base


class Statement(Base):
    """Statements table - tracks uploaded bank statements"""
    __tablename__ = 'statements'

    id = Column(Integer, primary_key=True, index=True)
    tax_entity_id = Column(Integer, nullable=False, index=True)
    bank_name = Column(String(255), nullable=False)
    statement_date = Column(String(50))
    file_hash = Column(String(64), unique=True, index=True)
    transaction_count = Column(Integer, default=0)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())


class StagingTransaction(Base):
    """Staging transactions table - holds parsed transactions for review"""
    __tablename__ = 'staging_transactions'

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False, index=True)
    tax_entity_id = Column(Integer, nullable=False, index=True)
    date = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    currency_code = Column(String(3))
    status = Column(String(50), default='pending_review', index=True)
    line_number = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
