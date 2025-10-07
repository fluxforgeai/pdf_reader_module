"""Test all Capitec bank statements with OCR"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import parse_bank_statement

def test_all_statements():
    """Test all PDF statements in bank_statements directory"""
    statements_dir = Path("bank_statements")

    if not statements_dir.exists():
        print("Error: bank_statements/ directory not found")
        return

    pdf_files = sorted(statements_dir.glob("*.pdf"))

    print("="  * 80)
    print("CAPITEC BANK STATEMENTS - OCR TESTING")
    print("=" * 80)
    print(f"\nFound {len(pdf_files)} PDF files\n")

    results = []

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        print("-" * 80)

        try:
            result = parse_bank_statement(str(pdf_file), "Capitec Bank", use_ocr=False)  # Auto-detect

            results.append({
                'file': pdf_file.name,
                'count': result['transaction_count'],
                'date': result['statement_date'],
                'total': sum(t['amount'] for t in result['transactions']),
                'ocr_used': result.get('ocr_used', False)
            })

            print(f"✓ Statement Date: {result['statement_date']}")
            print(f"✓ Transactions: {result['transaction_count']}")
            print(f"✓ Total Amount: R{sum(t['amount'] for t in result['transactions']):.2f}")
            print(f"✓ OCR Used: {result.get('ocr_used', 'Auto-detected')}")

            # Show sample transactions
            if result['transactions']:
                print(f"\nSample transactions:")
                for txn in result['transactions'][:3]:
                    print(f"  - {txn['date']}: {txn['description'][:50]}... R{txn['amount']:.2f}")

        except Exception as e:
            print(f"✗ Error: {str(e)}")
            results.append({
                'file': pdf_file.name,
                'error': str(e)
            })

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_transactions = 0
    total_amount = 0.0

    for r in results:
        if 'count' in r:
            print(f"{r['file']:40s} {r['count']:3d} txns   R{r['total']:10.2f}")
            total_transactions += r['count']
            total_amount += r['total']
        else:
            print(f"{r['file']:40s} ERROR: {r.get('error', 'Unknown')}")

    print("-" * 80)
    print(f"{'TOTAL':40s} {total_transactions:3d} txns   R{total_amount:10.2f}")
    print("=" * 80)

if __name__ == "__main__":
    test_all_statements()
