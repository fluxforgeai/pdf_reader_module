"""Analyze Capitec bank statement structure"""

import sys
import pdfplumber
import re

def analyze_statement(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:2], 1):  # Just first 2 pages
            print(f"\n{'='*80}")
            print(f"PAGE {page_num}")
            print('='*80)

            text = page.extract_text()
            lines = text.split('\n')

            print("\nLooking for potential transaction patterns...")
            print("-" * 80)

            for i, line in enumerate(lines, 1):
                # Look for lines with "POS" or amounts
                if 'onr' in line.lower() or 'pos' in line.lower():
                    print(f"{i:3d}: {line}")

                # Look for lines with currency amounts (L prefix seems to be R for Rand)
                if re.search(r'[LJ][R?\d]+[.,]\d{2}', line):
                    print(f"{i:3d}: {line}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_capitec.py <pdf_path>")
        sys.exit(1)

    analyze_statement(sys.argv[1])
