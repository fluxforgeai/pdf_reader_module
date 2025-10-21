"""Pydantic models for API request/response schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Transaction(BaseModel):
    """Single transaction record"""
    date: str  # Kept for backward compatibility
    description: str
    amount: float
    line_number: int

    # Extended fields for 7-column bank statement format
    post_date: Optional[str] = None
    trans_date: Optional[str] = None
    reference: Optional[str] = None
    fees: Optional[float] = None
    balance: Optional[float] = None

    # Editable fields
    original_description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    is_edited: bool = False


class Category(BaseModel):
    """Transaction category"""
    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class TransactionEdit(BaseModel):
    """Request to edit a transaction's description and category"""
    transaction_index: int  # Index in the statement
    new_description: str
    category_id: Optional[int] = None
    learn_pattern: bool = True  # Whether to learn this as a pattern


class TransactionUpdate(BaseModel):
    """Request to update a saved transaction"""
    description: Optional[str] = None
    category_id: Optional[int] = None


class SuggestionRequest(BaseModel):
    """Request for AI suggestions"""
    description: str
    reference: str = ""


class SuggestionResponse(BaseModel):
    """Suggested changes for a transaction"""
    suggested_description: Optional[str] = None
    suggested_category_id: Optional[int] = None
    suggested_category_name: Optional[str] = None
    confidence: float = 0.0
    pattern_matched: Optional[str] = None


class ParseResponse(BaseModel):
    """Response from /parse endpoint - preview before committing"""
    bank_name: str
    statement_date: Optional[str]
    transaction_count: int
    transactions: List[Transaction]
    total_amount: float = Field(description="Sum of all transaction amounts")
    ocr_used: bool = Field(default=False, description="Whether OCR was used for text extraction")


class ConfirmRequest(BaseModel):
    """Request to confirm and insert parsed data into database"""
    bank_name: str
    statement_date: Optional[str]
    tax_entity_id: int
    transactions: List[Transaction]


class ConfirmResponse(BaseModel):
    """Response from /confirm endpoint"""
    statement_id: int
    inserted_count: int
    message: str


class CategoryUpdate(BaseModel):
    """Request to update a category"""
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
