"""
Core Transaction Detection Algorithm for PDF Bank Statements

This module implements layered heuristics to detect transaction patterns:
- Date anchor: Identifies lines starting with date patterns
- Amount anchor: Detects currency amounts
- Multi-line handling: Concatenates wrapped descriptions
- OCR fallback: Handles garbled or scanned PDFs

Target: 70% accuracy threshold (good enough to beat manual entry)
"""

import re
from typing import List, Dict, Optional
from datetime import datetime
import pdfplumber
from .ocr_processor import extract_text_with_fallback


class TransactionDetector:
    """Detects and parses transactions from bank statement PDFs using layered heuristics."""

    # Date patterns - supports common formats
    DATE_PATTERNS = [
        r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',      # MM/DD/YYYY or DD/MM/YYYY
        r'\b(\d{1,2}-\d{1,2}-\d{2,4})\b',      # MM-DD-YYYY or DD-MM-YYYY
        r'\b(\d{4}-\d{1,2}-\d{1,2})\b',        # YYYY-MM-DD
        r'\b(\d{1,2}\.\d{1,2}\.\d{2,4})\b',    # DD.MM.YYYY
        r'\b([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})\b',  # Jan 15, 2024
    ]

    # Amount patterns - handles currency symbols, negatives, commas
    AMOUNT_PATTERNS = [
        r'[\$€£¥]\s*-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $1,234.56 or -$1,234.56
        r'-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[\$€£¥]',  # 1,234.56$ or -1,234.56$
        r'-?\d{1,3}(?:,\d{3})*\.\d{2}\b',               # 1,234.56 (no symbol)
        r'\(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',          # (1,234.56) - accounting negative
    ]

    def __init__(self):
        self.date_regex = re.compile('|'.join(self.DATE_PATTERNS))
        self.amount_regex = re.compile('|'.join(self.AMOUNT_PATTERNS))

    def extract_text_from_pdf(self, pdf_path: str, use_ocr: bool = False) -> List[str]:
        """
        Extract text from PDF with OCR fallback.

        Args:
            pdf_path: Path to PDF file
            use_ocr: Force OCR mode (skip standard extraction)

        Returns:
            List of text lines
        """
        # Use OCR-aware extraction with automatic fallback
        return extract_text_with_fallback(pdf_path, use_ocr=use_ocr)

    def is_date_line(self, line: str) -> Optional[str]:
        """Check if line starts with a date pattern. Returns date string if found."""
        match = self.date_regex.search(line)
        if match:
            # Check if date is at the beginning of the line (with some tolerance)
            if match.start() < 20:  # Date should be near start
                return match.group(0)
        return None

    def extract_amount(self, line: str) -> Optional[float]:
        """Extract currency amount from line. Returns float value."""
        match = self.amount_regex.search(line)
        if match:
            amount_str = match.group(0)

            # Handle accounting negatives (parentheses)
            if amount_str.startswith('(') and amount_str.endswith(')'):
                amount_str = '-' + amount_str[1:-1]

            # Remove currency symbols and commas
            amount_str = re.sub(r'[\$€£¥,\s]', '', amount_str)

            try:
                return float(amount_str)
            except ValueError:
                return None
        return None

    def extract_description(self, line: str, date_str: str, amount_str: str) -> str:
        """Extract description by removing date and amount from line."""
        # Remove date
        desc = line.replace(date_str, '', 1)

        # Remove amount pattern
        desc = self.amount_regex.sub('', desc)

        # Clean up whitespace
        desc = ' '.join(desc.split())

        return desc.strip()

    def parse_transactions(self, pdf_path: str, use_ocr: bool = False) -> List[Dict]:
        """
        Main parsing method using layered heuristics.

        Args:
            pdf_path: Path to PDF file
            use_ocr: Force OCR mode for text extraction

        Returns list of transaction dicts: [{date, description, amount}, ...]
        """
        lines = self.extract_text_from_pdf(pdf_path, use_ocr=use_ocr)
        transactions = []
        current_transaction = None

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            if not line:
                continue

            # Date anchor: Check if line starts with date
            date_str = self.is_date_line(line)
            amount = self.extract_amount(line)

            # Complete transaction pattern: Date AND Amount
            if date_str and amount is not None:
                # Save previous transaction if exists
                if current_transaction:
                    transactions.append(current_transaction)

                # Start new transaction
                description = self.extract_description(line, date_str, str(amount))
                current_transaction = {
                    'date': date_str,
                    'description': description,
                    'amount': amount,
                    'line_number': line_num
                }

            # Multi-line handling: Line with amount but no date = continuation
            elif amount is not None and not date_str and current_transaction:
                # This might be a wrapped description with amount on next line
                # Update amount and append description
                current_transaction['amount'] = amount
                desc_part = self.amount_regex.sub('', line).strip()
                if desc_part:
                    current_transaction['description'] += ' ' + desc_part

            # Description continuation: No date, no amount = append to description
            elif not date_str and amount is None and current_transaction:
                # Check for leading whitespace (indentation indicates continuation)
                if line[0].isspace() or len(line) < 30:  # Short lines likely continuations
                    current_transaction['description'] += ' ' + line.strip()

        # Don't forget the last transaction
        if current_transaction:
            transactions.append(current_transaction)

        return transactions

    def extract_statement_date(self, pdf_path: str) -> Optional[str]:
        """Extract statement date from first 10 lines of PDF."""
        lines = self.extract_text_from_pdf(pdf_path)[:10]

        for line in lines:
            # Look for "Statement Date", "As of", "Period Ending", etc.
            if any(keyword in line.lower() for keyword in ['statement date', 'as of', 'period ending', 'date:']):
                date_match = self.date_regex.search(line)
                if date_match:
                    return date_match.group(0)

        # Fallback: return first date found
        for line in lines:
            date_match = self.date_regex.search(line)
            if date_match:
                return date_match.group(0)

        return None


def parse_bank_statement(pdf_path: str, bank_name: str, use_ocr: bool = False) -> Dict:
    """
    Convenience function for parsing bank statements with OCR support.

    Args:
        pdf_path: Path to PDF file
        bank_name: Bank name (manually provided by user)
        use_ocr: Force OCR mode (auto-detects garbled text by default)

    Returns:
        Dict with metadata and transactions:
        {
            'bank_name': str,
            'statement_date': str,
            'transaction_count': int,
            'transactions': [...],
            'ocr_used': bool
        }
    """
    detector = TransactionDetector()

    transactions = detector.parse_transactions(pdf_path, use_ocr=use_ocr)
    statement_date = detector.extract_statement_date(pdf_path)

    return {
        'bank_name': bank_name,
        'statement_date': statement_date,
        'transaction_count': len(transactions),
        'transactions': transactions,
        'ocr_used': use_ocr  # Track if OCR was used
    }
