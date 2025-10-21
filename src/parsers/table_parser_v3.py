"""
Final Table-Aware PDF Parser - Simple and Effective

Based on actual OCR output analysis, Capitec statements have all data on single lines.
Format: PostDate TransDate Description Reference Fees Amount Balance
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pdfplumber
import pytesseract
from pdf2image import convert_from_path


@dataclass
class BankTransaction:
    """Represents a single bank transaction"""
    post_date: str
    trans_date: str
    description: str
    reference: str
    fees: Optional[float]
    amount: float
    balance: float
    line_number: int

    def to_dict(self) -> Dict:
        return {
            "post_date": self.post_date,
            "trans_date": self.trans_date,
            "description": self.description,
            "reference": self.reference,
            "fees": self.fees,
            "amount": self.amount,
            "balance": self.balance,
            "line_number": self.line_number
        }


class TableParserV3:
    """
    Parser optimized for Capitec bank statements with OCR.

    Expected format per line:
    DD/MM/YY DD/MM/YY Description Reference -Fees -Amount +Balance
    """

    # Date pattern
    DATE_PATTERN = re.compile(r'\b(\d{2}/\d{2}/\d{2})\b')

    # Amount pattern (handles -7.50 and -10 000.00, and +124 345.00)
    # Need to handle both commas and spaces in thousands
    # Also need to match standalone decimals like .00
    AMOUNT_PATTERN = re.compile(r'[+-]?\d{1,3}(?:[\s,]\d{3})*\.\d{2}|[+-]\d+\.\d{2}')

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def parse_bank_statement(self, pdf_path: str) -> Tuple[List[BankTransaction], bool]:
        """Parse bank statement from PDF"""
        # Check if garbled
        with pdfplumber.open(pdf_path) as pdf:
            sample_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
            is_garbled = self._is_text_garbled(sample_text)

        if not is_garbled:
            # Use standard extraction (not implemented for now)
            return [], False

        print("⚠️  Garbled text detected, using OCR for extraction...")

        # Convert PDF to images and OCR
        images = convert_from_path(pdf_path, dpi=300)

        all_transactions = []
        line_number = 0

        for page_num, image in enumerate(images, 1):
            # Get OCR text
            ocr_text = pytesseract.image_to_string(
                image,
                lang='eng',
                config='--oem 3 --psm 6'
            )

            # Parse transactions from this page
            page_transactions = self._parse_page(ocr_text, line_number)
            all_transactions.extend(page_transactions)
            line_number += len(page_transactions)

        return all_transactions, True

    def _parse_page(self, text: str, start_line: int) -> List[BankTransaction]:
        """Parse transactions from OCR text of one page"""
        transactions = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for lines starting with two dates
            dates = self.DATE_PATTERN.findall(line)

            if len(dates) >= 2:
                # This is likely a transaction line
                transaction = self._parse_transaction_line(line, dates, len(transactions) + start_line + 1)
                if transaction:
                    transactions.append(transaction)

        return transactions

    def _parse_transaction_line(self, line: str, dates: List[str], line_number: int) -> Optional[BankTransaction]:
        """
        Parse a single transaction line.

        Expected format:
        07/06/23 07/06/23 ******006073** ** Directors Fees Artiligence -7.50 -10000.00, +114 337.50
        """
        try:
            post_date = dates[0]
            trans_date = dates[1]

            # Find all amounts in the line
            amounts = self.AMOUNT_PATTERN.findall(line)

            # Should have 3 amounts: fees, amount, balance
            if len(amounts) < 2:
                return None  # Need at least amount and balance

            # Parse amounts (remove spaces and commas)
            parsed_amounts = []
            for amt_str in amounts:
                amt_clean = amt_str.replace(' ', '').replace(',', '')
                try:
                    parsed_amounts.append(float(amt_clean))
                except ValueError:
                    continue

            if len(parsed_amounts) < 2:
                return None

            # Last amount is always balance (positive)
            balance = parsed_amounts[-1]

            # Second to last is the transaction amount (negative for debits)
            amount = parsed_amounts[-2]

            # If there's a third amount, it's fees
            fees = parsed_amounts[-3] if len(parsed_amounts) >= 3 else None

            # Extract description and reference
            # Remove dates from start
            remainder = line
            for date in dates[:2]:
                remainder = remainder.replace(date, '', 1)

            # Remove the last 3 amounts from end (fees, amount, balance)
            # Work backwards to avoid partial matches
            for amt in amounts[-3:]:
                # Find last occurrence
                idx = remainder.rfind(amt)
                if idx != -1:
                    remainder = remainder[:idx] + remainder[idx+len(amt):]

            # Split remainder into parts
            parts = remainder.strip().split()

            # Find reference pattern (looks like: 0000000000002667 or A0159924 or ***006073**)
            reference = ""
            description_parts = []

            for i, part in enumerate(parts):
                # Check if looks like a reference code
                # Patterns: all digits (8+), alphanumeric starting with letter (6+), or stars+digits
                is_reference = False

                if len(part) >= 8:
                    # Pattern: 0000000000002667 (many zeros/digits)
                    if part.isdigit() or part.replace('*', '').replace('0', '').isdigit():
                        is_reference = True
                    # Pattern: A0159924 (letter followed by digits)
                    elif part[0].isalpha() and part[1:].isdigit():
                        is_reference = True
                    # Pattern: ******006073**
                    elif '*' in part and any(c.isdigit() for c in part):
                        is_reference = True

                if is_reference and not reference:
                    reference = part
                else:
                    description_parts.append(part)

            description = ' '.join(description_parts).strip()

            # Filter out obviously bad transactions
            if not description or len(description) < 3:
                return None

            # Skip header rows
            if 'balance brought forward' in description.lower():
                return None
            if 'interest rate' in description.lower():
                return None

            return BankTransaction(
                post_date=post_date,
                trans_date=trans_date,
                description=description,
                reference=reference,
                fees=fees,
                amount=amount,
                balance=balance,
                line_number=line_number
            )

        except (IndexError, ValueError) as e:
            return None

    def _is_text_garbled(self, text: str, threshold: float = 0.2) -> bool:
        """Detect if text is garbled"""
        if not text:
            return False

        non_ascii = sum(1 for char in text if ord(char) > 127)
        total = len(text)

        if total > 0 and (non_ascii / total) > threshold:
            return True

        garbled_indicators = ['???', 'ï¿½', '¶', '†', 'ƒ', '⁄', '…', '§', '•']
        if any(indicator in text for indicator in garbled_indicators):
            return True

        return False
