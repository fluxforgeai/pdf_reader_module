"""FastAPI endpoints for bank statement processing"""

import os
import tempfile
from typing import Annotated
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import ParseResponse, ConfirmRequest, ConfirmResponse, ErrorResponse, Transaction
from ..parsers import parse_bank_statement
from ..db import (
    get_db,
    calculate_file_hash,
    get_currency_code,
    create_statement,
    bulk_insert_transactions,
    check_duplicate_statement
)

router = APIRouter(prefix="/api/statements", tags=["statements"])


@router.post("/parse", response_model=ParseResponse)
async def parse_statement(
    file: Annotated[UploadFile, File(description="PDF bank statement file")],
    bank_name: Annotated[str, Form(description="Bank name (manually provided)")],
    use_ocr: Annotated[bool, Form(description="Force OCR mode (auto-detects by default)")] = False,
    db: Session = Depends(get_db)
):
    """
    Parse PDF bank statement and return preview of transactions.

    This endpoint:
    1. Validates PDF file
    2. Extracts transactions using heuristic parser with OCR fallback
    3. Returns JSON preview WITHOUT writing to database

    User reviews the preview before confirming via /confirm endpoint.

    OCR Support:
    - Auto-detects garbled text and falls back to OCR
    - Set use_ocr=true to force OCR mode
    - Critical for Capitec and other banks with encoding issues
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    try:
        # Read file content
        content = await file.read()

        # Check for duplicate
        file_hash = calculate_file_hash(content)
        if check_duplicate_statement(db, file_hash):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This statement has already been imported (duplicate file hash)"
            )

        # Save to temporary file for pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Parse the statement with OCR support
            result = parse_bank_statement(tmp_path, bank_name, use_ocr=use_ocr)

            # Calculate total amount
            total_amount = sum(txn['amount'] for txn in result['transactions'])

            # Build response
            response = ParseResponse(
                bank_name=result['bank_name'],
                statement_date=result['statement_date'],
                transaction_count=result['transaction_count'],
                transactions=[Transaction(**txn) for txn in result['transactions']],
                total_amount=total_amount,
                ocr_used=result.get('ocr_used', False)
            )

            return response

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse PDF: {str(e)}"
        )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_statement(
    request: ConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm parsed transactions and insert into database.

    This endpoint:
    1. Creates statement record
    2. Bulk inserts transactions into staging_transactions
    3. Links via statement_id foreign key
    4. Infers currency from tax_entity

    Called after user reviews and approves the preview from /parse.
    """
    try:
        # Get currency code from tax entity
        currency_code = get_currency_code(db, request.tax_entity_id)

        # Create statement record
        # Note: file_hash is not available here (not sent in confirm request)
        # In production, you'd want to include it in the preview response
        # and send it back in the confirm request
        statement = create_statement(
            db=db,
            tax_entity_id=request.tax_entity_id,
            bank_name=request.bank_name,
            statement_date=request.statement_date,
            file_hash="",  # Would be passed from parse response in production
            transaction_count=len(request.transactions)
        )

        # Bulk insert transactions
        transactions_data = [txn.model_dump() for txn in request.transactions]
        inserted_count = bulk_insert_transactions(
            db=db,
            statement_id=statement.id,
            tax_entity_id=request.tax_entity_id,
            transactions=transactions_data,
            currency_code=currency_code
        )

        return ConfirmResponse(
            statement_id=statement.id,
            inserted_count=inserted_count,
            message=f"Successfully imported {inserted_count} transactions"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert transactions: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "bank-statement-parser"}
