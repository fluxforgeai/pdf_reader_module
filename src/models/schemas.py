"""Pydantic models for API request/response schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Transaction(BaseModel):
    """Single transaction record"""
    date: str
    description: str
    amount: float
    line_number: int


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


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
