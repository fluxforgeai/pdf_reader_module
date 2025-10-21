"""Database operations for statements and transactions"""

import hashlib
from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Statement, StagingTransaction


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content for duplicate detection"""
    return hashlib.sha256(file_content).hexdigest()


def get_currency_code(db: Session, tax_entity_id: int) -> Optional[str]:
    """
    Infer currency code from tax_entities table based on country.
    Returns None if not found or table doesn't exist yet.
    """
    try:
        # This assumes tax_entities table exists with currency_code column
        # If not, this will be handled gracefully
        result = db.execute(
            "SELECT currency_code FROM tax_entities WHERE id = :id",
            {"id": tax_entity_id}
        ).fetchone()
        return result[0] if result else None
    except Exception:
        # Table might not exist yet - return None
        return None


def create_statement(
    db: Session,
    tax_entity_id: int,
    bank_name: str,
    statement_date: Optional[str],
    file_hash: str,
    transaction_count: int
) -> Statement:
    """Create new statement record"""
    statement = Statement(
        tax_entity_id=tax_entity_id,
        bank_name=bank_name,
        statement_date=statement_date,
        file_hash=file_hash,
        transaction_count=transaction_count
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


def bulk_insert_transactions(
    db: Session,
    statement_id: int,
    tax_entity_id: int,
    transactions: List[dict],
    currency_code: Optional[str] = None
) -> int:
    """
    Bulk insert transactions into staging_transactions table.
    Returns count of inserted records.

    Supports both legacy (date, description, amount) and extended
    (post_date, trans_date, reference, fees, balance) formats.
    """
    staging_transactions = []

    for txn in transactions:
        staging_txn = StagingTransaction(
            statement_id=statement_id,
            tax_entity_id=tax_entity_id,
            date=txn['date'],
            description=txn['description'],
            amount=txn['amount'],
            currency_code=currency_code,
            status='pending_review',
            line_number=txn.get('line_number'),
            # Extended fields (optional)
            post_date=txn.get('post_date'),
            trans_date=txn.get('trans_date'),
            reference=txn.get('reference'),
            fees=txn.get('fees'),
            balance=txn.get('balance')
        )
        staging_transactions.append(staging_txn)

    db.bulk_save_objects(staging_transactions)
    db.commit()

    return len(staging_transactions)


def check_duplicate_statement(db: Session, file_hash: str) -> bool:
    """Check if statement with this file hash already exists"""
    existing = db.query(Statement).filter(Statement.file_hash == file_hash).first()
    return existing is not None
