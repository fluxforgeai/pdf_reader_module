"""FastAPI endpoints for bank statement processing"""

import os
import tempfile
from typing import Annotated, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import (ParseResponse, ConfirmRequest, ConfirmResponse, ErrorResponse,
                      Transaction, Category, CategoryUpdate, TransactionEdit, TransactionUpdate,
                      SuggestionRequest, SuggestionResponse)
from ..parsers import parse_bank_statement
from ..db import (
    get_db,
    calculate_file_hash,
    get_currency_code,
    create_statement,
    bulk_insert_transactions,
    check_duplicate_statement
)
from ..services import CategorizationService

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


@router.post("/debug-parse")
async def debug_parse_statement(
    file: Annotated[UploadFile, File(description="PDF bank statement file")],
    bank_name: Annotated[str, Form(description="Bank name")],
    use_ocr: Annotated[bool, Form(description="Force OCR mode")] = False
):
    """
    Debug endpoint that returns raw text lines, table data, and parse results.
    Useful for debugging parsing issues.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    try:
        content = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            import pdfplumber
            from ..parsers.transaction_detector import TransactionDetector

            # Get raw text lines
            detector = TransactionDetector()
            raw_lines = detector.extract_text_from_pdf(tmp_path, use_ocr=use_ocr)

            # Extract table structure
            tables_data = []
            with pdfplumber.open(tmp_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:3], 1):  # First 3 pages
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            tables_data.append({
                                "page": page_num,
                                "table_num": table_num,
                                "rows": len(table),
                                "columns": len(table[0]) if table else 0,
                                "headers": table[0] if table else [],
                                "data": table[1:20] if len(table) > 1 else []  # First 20 rows
                            })

            return {
                "raw_lines": raw_lines,
                "total_lines": len(raw_lines),
                "tables": tables_data,
                "tables_found": len(tables_data)
            }

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {str(e)}"
        )


@router.post("/parse-batch")
async def parse_batch_statements(
    files: Annotated[List[UploadFile], File(description="Multiple PDF bank statement files")],
    bank_name: Annotated[str, Form(description="Bank name (applied to all statements)")],
    use_ocr: Annotated[bool, Form(description="Force OCR mode (auto-detects by default)")] = False,
    db: Session = Depends(get_db)
):
    """
    Parse multiple PDF bank statements and return preview of all transactions.

    This endpoint:
    1. Validates all PDF files
    2. Extracts transactions from each statement
    3. Returns JSON preview for each statement WITHOUT writing to database
    4. Checks for duplicates before parsing

    Returns a list of ParseResponse objects, one per statement.
    User reviews all statements before confirming via /confirm endpoint.
    """
    results = []
    errors = []

    for file in files:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            errors.append({
                "filename": file.filename,
                "error": "Only PDF files are supported"
            })
            continue

        try:
            # Read file content
            content = await file.read()

            # Check for duplicate
            file_hash = calculate_file_hash(content)
            if check_duplicate_statement(db, file_hash):
                errors.append({
                    "filename": file.filename,
                    "error": "This statement has already been imported (duplicate file hash)"
                })
                continue

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
                response = {
                    "filename": file.filename,
                    "file_hash": file_hash,
                    "bank_name": result['bank_name'],
                    "statement_date": result['statement_date'],
                    "transaction_count": result['transaction_count'],
                    "transactions": [Transaction(**txn).model_dump() for txn in result['transactions']],
                    "total_amount": total_amount,
                    "ocr_used": result.get('ocr_used', False)
                }

                results.append(response)

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": f"Failed to parse: {str(e)}"
            })

    return {
        "success_count": len(results),
        "error_count": len(errors),
        "statements": results,
        "errors": errors
    }


@router.get("/categories", response_model=List[Category])
async def get_categories(db: Session = Depends(get_db)):
    """Get all available transaction categories"""
    service = CategorizationService(db)
    categories = service.get_all_categories()
    return categories


@router.post("/categories", response_model=Category)
async def create_category(
    category: Category,
    db: Session = Depends(get_db)
):
    """Create a new transaction category"""
    service = CategorizationService(db)
    category_id = service.create_category(
        name=category.name,
        parent_id=category.parent_id,
        color=category.color,
        icon=category.icon
    )
    category.id = category_id
    return category


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    update_data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing transaction category"""
    service = CategorizationService(db)
    success = service.update_category(
        category_id=category_id,
        name=update_data.name,
        color=update_data.color,
        icon=update_data.icon
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )

    return {"message": "Category updated successfully", "category_id": category_id}


@router.post("/suggestions")
async def get_transaction_suggestions(
    request: SuggestionRequest,
    db: Session = Depends(get_db)
):
    """
    Get suggested improvements for a transaction description.

    This uses learned patterns to suggest:
    - Better formatted description
    - Appropriate category
    - Confidence level
    """
    service = CategorizationService(db)
    suggestions = service.find_suggestions(request.description, request.reference)
    return SuggestionResponse(**suggestions)


@router.post("/learn-pattern")
async def learn_from_edit(
    original_description: str,
    new_description: str,
    reference: str = "",
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Learn a new pattern from user's edit.

    This teaches the system how to automatically improve similar transactions.
    """
    service = CategorizationService(db)
    service.learn_pattern(
        original_description=original_description,
        new_description=new_description,
        reference=reference,
        category_id=category_id
    )
    return {"message": "Pattern learned successfully"}


@router.get("/list")
async def list_saved_statements(db: Session = Depends(get_db)):
    """
    Get all saved statements with their transactions.

    Returns statements in reverse chronological order (newest first).
    """
    from ..db.models import Statement, StagingTransaction, Category
    from sqlalchemy import desc

    try:
        # Get all statements ordered by import date (newest first)
        statements = db.query(Statement).order_by(desc(Statement.imported_at)).all()

        result = []
        for stmt in statements:
            # Get all transactions for this statement
            transactions = db.query(StagingTransaction).filter(
                StagingTransaction.statement_id == stmt.id
            ).order_by(StagingTransaction.line_number).all()

            # Get category info for each transaction
            trans_list = []
            for txn in transactions:
                category_name = None
                category_icon = None
                if txn.category_id:
                    category = db.query(Category).filter(Category.id == txn.category_id).first()
                    if category:
                        category_name = category.name
                        category_icon = category.icon

                trans_list.append({
                    "id": txn.id,
                    "date": txn.date,
                    "post_date": txn.post_date,
                    "trans_date": txn.trans_date,
                    "description": txn.description,
                    "original_description": txn.original_description,
                    "reference": txn.reference,
                    "fees": txn.fees,
                    "amount": txn.amount,
                    "balance": txn.balance,
                    "category_id": txn.category_id,
                    "category_name": category_name,
                    "category_icon": category_icon,
                    "is_edited": txn.is_edited,
                    "line_number": txn.line_number
                })

            result.append({
                "id": stmt.id,
                "bank_name": stmt.bank_name,
                "statement_date": stmt.statement_date,
                "transaction_count": stmt.transaction_count,
                "imported_at": stmt.imported_at.isoformat() if stmt.imported_at else None,
                "transactions": trans_list
            })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statements: {str(e)}"
        )


@router.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    update_data: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a saved transaction's description and/or category.

    This allows editing transactions that are already in the database.
    Triggers pattern learning if description is changed.
    """
    from ..db.models import StagingTransaction

    try:
        # Find the transaction
        transaction = db.query(StagingTransaction).filter(
            StagingTransaction.id == transaction_id
        ).first()

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with id {transaction_id} not found"
            )

        # Store original for pattern learning
        original_description = transaction.original_description or transaction.description

        # Update fields
        if update_data.description is not None and update_data.description != transaction.description:
            # Store original if not already stored
            if not transaction.original_description:
                transaction.original_description = transaction.description

            transaction.description = update_data.description
            transaction.is_edited = True

            # Trigger pattern learning
            if update_data.category_id is not None:
                service = CategorizationService(db)
                service.learn_pattern(
                    original_description=original_description,
                    new_description=update_data.description,
                    reference=transaction.reference or "",
                    category_id=update_data.category_id
                )

        if update_data.category_id is not None:
            transaction.category_id = update_data.category_id

        db.commit()
        db.refresh(transaction)

        return {
            "message": "Transaction updated successfully",
            "transaction_id": transaction_id,
            "description": transaction.description,
            "category_id": transaction.category_id,
            "is_edited": transaction.is_edited
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update transaction: {str(e)}"
        )
