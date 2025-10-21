"""PDF Bank Statement Parser Module"""

from .table_parser_v3 import TableParserV3
from typing import Dict

def parse_bank_statement(pdf_path: str, bank_name: str, use_ocr: bool = False) -> Dict:
    """
    Parse bank statement from PDF using OCR-enabled table parser.

    Args:
        pdf_path: Path to PDF file
        bank_name: Bank name (manually provided by user)
        use_ocr: Force OCR mode (auto-detects garbled text by default)

    Returns:
        Dict with metadata and transactions
    """
    parser = TableParserV3()
    transactions, ocr_used = parser.parse_bank_statement(pdf_path)

    # Convert BankTransaction objects to dicts
    transaction_dicts = []
    for txn in transactions:
        transaction_dicts.append({
            'date': txn.trans_date,
            'description': txn.description,
            'amount': txn.amount,
            'line_number': txn.line_number,
            'post_date': txn.post_date,
            'trans_date': txn.trans_date,
            'reference': txn.reference,
            'fees': txn.fees,
            'balance': txn.balance
        })

    # Extract statement date from first transaction
    statement_date = transactions[0].post_date if transactions else None

    return {
        'bank_name': bank_name,
        'statement_date': statement_date,
        'transaction_count': len(transaction_dicts),
        'transactions': transaction_dicts,
        'ocr_used': ocr_used
    }

__all__ = ['TableParserV3', 'parse_bank_statement']
