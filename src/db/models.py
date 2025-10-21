"""SQLAlchemy ORM models for database tables"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
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
    date = Column(String(50), nullable=False)  # Kept for backward compatibility
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    currency_code = Column(String(3))
    status = Column(String(50), default='pending_review', index=True)
    line_number = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Extended fields for 7-column bank statement format
    post_date = Column(String(50))
    trans_date = Column(String(50))
    reference = Column(String(255))
    fees = Column(Float)
    balance = Column(Float)

    # User edits and categorization
    original_description = Column(Text)  # Store original for reference
    category_id = Column(Integer, ForeignKey('categories.id'), index=True)
    is_edited = Column(Boolean, default=False)


class Category(Base):
    """Transaction categories for classification"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))  # For subcategories
    color = Column(String(7))  # Hex color like #FF5733
    icon = Column(String(50))  # Icon name/emoji
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TransactionPattern(Base):
    """Learned patterns for auto-categorization and description enhancement"""
    __tablename__ = 'transaction_patterns'

    id = Column(Integer, primary_key=True, index=True)

    # Pattern matching
    pattern_type = Column(String(50), nullable=False)  # 'contains', 'starts_with', 'regex', etc.
    pattern_value = Column(String(255), nullable=False, index=True)  # The text/regex to match

    # Actions to take when pattern matches
    category_id = Column(Integer, ForeignKey('categories.id'))
    suggested_description = Column(Text)  # New description to suggest
    confidence = Column(Float, default=1.0)  # How confident (based on # of times learned)

    # Metadata
    times_applied = Column(Integer, default=0)  # Track usage
    times_accepted = Column(Integer, default=0)  # Track acceptance rate
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
