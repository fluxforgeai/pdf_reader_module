"""
Create a simple test PDF bank statement for sandbox testing.
Uses reportlab to generate a PDF with sample transactions.
"""

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    print("Installing reportlab...")
    import subprocess
    subprocess.run(["pip", "install", "reportlab"], check=True)
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas


def create_sample_bank_statement(filename="test_statement.pdf"):
    """Create a sample bank statement PDF with mock transactions"""

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "SAMPLE BANK")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "123 Main Street, Anytown, USA")
    c.drawString(50, height - 85, "Statement Date: 01/31/2024")
    c.drawString(50, height - 100, "Account Number: ****1234")

    # Separator
    c.line(50, height - 120, width - 50, height - 120)

    # Transaction header
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 140, "Date")
    c.drawString(150, height - 140, "Description")
    c.drawString(450, height - 140, "Amount")

    c.line(50, height - 145, width - 50, height - 145)

    # Sample transactions
    c.setFont("Helvetica", 10)
    transactions = [
        ("01/05/2024", "PAYROLL DEPOSIT", "2500.00"),
        ("01/06/2024", "SAFEWAY STORE #1234", "-87.23"),
        ("01/08/2024", "SHELL GAS STATION", "-45.50"),
        ("01/10/2024", "AMAZON.COM PURCHASE", "-156.78"),
        ("01/12/2024", "ATM WITHDRAWAL", "-100.00"),
        ("01/15/2024", "ELECTRIC COMPANY PAYMENT", "-123.45"),
        ("01/18/2024", "RESTAURANT - ITALIANO", "-89.50"),
        ("01/20/2024", "PAYROLL DEPOSIT", "2500.00"),
        ("01/22/2024", "TARGET STORE #5678", "-234.56"),
        ("01/25/2024", "PHARMACY CO-PAY", "-15.00"),
        ("01/28/2024", "MONTHLY RENT PAYMENT", "-1500.00"),
        ("01/30/2024", "GROCERY OUTLET", "-67.89"),
    ]

    y_position = height - 165
    for date, description, amount in transactions:
        c.drawString(50, y_position, date)
        c.drawString(150, y_position, description)

        # Right-align amounts
        if amount.startswith("-"):
            c.drawString(450, y_position, f"-${amount[1:]}")
        else:
            c.drawString(450, y_position, f"${amount}")

        y_position -= 20

    # Footer
    c.line(50, y_position - 10, width - 50, y_position - 10)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(150, y_position - 30, "Ending Balance:")
    c.drawString(450, y_position - 30, "$3,180.09")

    c.save()
    print(f"✓ Created test PDF: {filename}")
    print(f"  - 12 sample transactions")
    print(f"  - Statement date: 01/31/2024")
    print(f"  - Mix of deposits and withdrawals")


if __name__ == "__main__":
    create_sample_bank_statement()
