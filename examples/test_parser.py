"""
Simple test script to verify the transaction parser works.

This script demonstrates how to use the parser directly without the API.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import parse_bank_statement


def test_parser(pdf_path: str, bank_name: str):
    """Test the parser with a sample PDF"""
    print(f"Parsing: {pdf_path}")
    print(f"Bank: {bank_name}")
    print("-" * 60)

    try:
        result = parse_bank_statement(pdf_path, bank_name)

        print(f"\n✓ Statement Date: {result['statement_date']}")
        print(f"✓ Transaction Count: {result['transaction_count']}")
        print(f"\nFirst 5 transactions:")
        print("-" * 60)

        for i, txn in enumerate(result['transactions'][:5], 1):
            print(f"\n{i}. Date: {txn['date']}")
            print(f"   Description: {txn['description'][:60]}...")
            print(f"   Amount: ${txn['amount']:.2f}")
            print(f"   Line: {txn['line_number']}")

        print("\n" + "-" * 60)
        print(f"✓ Successfully parsed {result['transaction_count']} transactions")

        # Calculate total
        total = sum(txn['amount'] for txn in result['transactions'])
        print(f"✓ Total Amount: ${total:.2f}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_parser.py <pdf_path> <bank_name>")
        print("\nExample:")
        print("  python test_parser.py statement.pdf 'Wells Fargo'")
        sys.exit(1)

    pdf_path = sys.argv[1]
    bank_name = sys.argv[2]

    test_parser(pdf_path, bank_name)
