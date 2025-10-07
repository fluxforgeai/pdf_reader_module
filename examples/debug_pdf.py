"""Debug script to examine PDF structure and text extraction"""

import sys
import pdfplumber

def debug_pdf(pdf_path):
    print(f"Examining: {pdf_path}\n")
    print("=" * 80)

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")

        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{'='*80}")
            print(f"PAGE {page_num}")
            print('='*80)

            text = page.extract_text()
            if text:
                lines = text.split('\n')
                print(f"Total lines: {len(lines)}\n")
                print("First 30 lines:")
                print("-" * 80)
                for i, line in enumerate(lines[:30], 1):
                    print(f"{i:3d}: {line}")

                if len(lines) > 30:
                    print(f"\n... ({len(lines) - 30} more lines)")
            else:
                print("No text extracted (might be scanned image)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf.py <pdf_path>")
        sys.exit(1)

    debug_pdf(sys.argv[1])
