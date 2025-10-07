# Bank Statement Parser - Usage Guide

## Overview

This guide walks you through using the Bank Statement Parser API to extract transactions from PDF bank statements.

## Prerequisites

1. **Python 3.8+** installed
2. **PostgreSQL database** running (for Lederly integration)
3. **PDF bank statement** files to parse

## Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI - Web framework
- pdfplumber - PDF text extraction
- SQLAlchemy - Database ORM
- psycopg2 - PostgreSQL driver
- Pydantic - Data validation

### Step 2: Configure Database

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your database connection:
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/lederly
```

3. Initialize database tables:
```bash
python -m src.db.init_db
```

This creates:
- `statements` table - Tracks uploaded PDFs
- `staging_transactions` table - Holds parsed transactions

### Step 3: Start API Server

```bash
python -m src.main
```

Or with auto-reload for development:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

## Using the API

### Option 1: Interactive API Documentation (Recommended)

Visit `http://localhost:8000/docs` in your browser to access the Swagger UI.

This provides:
- Interactive API testing
- Request/response examples
- Schema documentation

### Option 2: cURL Commands

#### Parse PDF Statement (Preview)

```bash
curl -X POST http://localhost:8000/api/statements/parse \
  -F "file=@/path/to/statement.pdf" \
  -F "bank_name=Wells Fargo"
```

**Response:**
```json
{
  "bank_name": "Wells Fargo",
  "statement_date": "01/31/2024",
  "transaction_count": 47,
  "total_amount": 12450.75,
  "transactions": [
    {
      "date": "01/05/2024",
      "description": "SAFEWAY STORE #1234",
      "amount": -87.23,
      "line_number": 15
    },
    {
      "date": "01/06/2024",
      "description": "PAYROLL DEPOSIT",
      "amount": 2500.00,
      "line_number": 17
    }
  ]
}
```

#### Confirm and Insert to Database

```bash
curl -X POST http://localhost:8000/api/statements/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "bank_name": "Wells Fargo",
    "statement_date": "01/31/2024",
    "tax_entity_id": 1,
    "transactions": [
      {
        "date": "01/05/2024",
        "description": "SAFEWAY STORE #1234",
        "amount": -87.23,
        "line_number": 15
      }
    ]
  }'
```

**Response:**
```json
{
  "statement_id": 42,
  "inserted_count": 1,
  "message": "Successfully imported 1 transactions"
}
```

### Option 3: Python Requests

```python
import requests

# Parse PDF
with open('statement.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/statements/parse',
        files={'file': f},
        data={'bank_name': 'Wells Fargo'}
    )

result = response.json()
print(f"Found {result['transaction_count']} transactions")

# Confirm and insert
confirm_response = requests.post(
    'http://localhost:8000/api/statements/confirm',
    json={
        'bank_name': result['bank_name'],
        'statement_date': result['statement_date'],
        'tax_entity_id': 1,
        'transactions': result['transactions']
    }
)

print(confirm_response.json())
```

## Typical Workflow

### 1. Upload and Parse

User uploads PDF bank statement via frontend:

```javascript
const formData = new FormData();
formData.append('file', pdfFile);
formData.append('bank_name', 'Chase Bank');

const response = await fetch('/api/statements/parse', {
  method: 'POST',
  body: formData
});

const preview = await response.json();
```

### 2. Display Preview

Show parsed transactions to user for review:

```javascript
console.log(`Statement Date: ${preview.statement_date}`);
console.log(`Transactions: ${preview.transaction_count}`);
console.log(`Total: $${preview.total_amount}`);

// Display transactions in table for user review/editing
preview.transactions.forEach(txn => {
  console.log(`${txn.date} - ${txn.description}: $${txn.amount}`);
});
```

### 3. User Reviews and Edits

User can:
- Verify transaction dates are correct
- Fix description typos or clarify merchants
- Correct amounts if parsing errors occurred
- Remove duplicate or invalid transactions

### 4. Confirm and Save

Once user approves, send to confirm endpoint:

```javascript
const confirmResponse = await fetch('/api/statements/confirm', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    bank_name: preview.bank_name,
    statement_date: preview.statement_date,
    tax_entity_id: currentTaxEntityId,
    transactions: editedTransactions  // User's edited version
  })
});

const result = await confirmResponse.json();
console.log(result.message);  // "Successfully imported 47 transactions"
```

## Testing the Parser

### Direct Parser Test (No API)

```bash
python examples/test_parser.py statement.pdf "Bank Name"
```

This runs the parser directly and shows:
- Statement date extracted
- Transaction count
- First 5 transactions
- Total amount

### API Test Script

```bash
./examples/test_api.sh statement.pdf
```

This tests:
- Health check endpoint
- Parse endpoint with sample PDF
- Root endpoint

## Understanding the Data Flow

```
┌─────────────┐
│  PDF File   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  POST /api/statements/parse │
│  - Extract text with        │
│    pdfplumber               │
│  - Apply heuristics         │
│  - Return JSON preview      │
└──────────┬──────────────────┘
           │
           ▼
    ┌──────────────┐
    │ User Reviews │
    │  & Edits     │
    └──────┬───────┘
           │
           ▼
┌──────────────────────────────┐
│ POST /api/statements/confirm │
│  - Create statement record   │
│  - Bulk insert transactions  │
│  - Link via statement_id     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│      PostgreSQL Database     │
│  ┌────────────────────────┐  │
│  │  statements            │  │
│  │  - id                  │  │
│  │  - bank_name           │  │
│  │  - statement_date      │  │
│  │  - file_hash           │  │
│  └──────────┬─────────────┘  │
│             │                │
│             │ FK: statement_id
│             │                │
│  ┌──────────▼─────────────┐  │
│  │  staging_transactions  │  │
│  │  - date                │  │
│  │  - description         │  │
│  │  - amount              │  │
│  │  - status              │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

## Querying Parsed Data

### View All Statements

```sql
SELECT id, bank_name, statement_date, transaction_count, imported_at
FROM statements
ORDER BY imported_at DESC;
```

### View Transactions for a Statement

```sql
SELECT date, description, amount, currency_code, status
FROM staging_transactions
WHERE statement_id = 42
ORDER BY line_number;
```

### Find Pending Review Transactions

```sql
SELECT s.bank_name, s.statement_date, st.date, st.description, st.amount
FROM staging_transactions st
JOIN statements s ON st.statement_id = s.id
WHERE st.status = 'pending_review'
ORDER BY s.imported_at DESC, st.line_number;
```

### Update Transaction Status

```sql
-- Mark as validated
UPDATE staging_transactions
SET status = 'validated'
WHERE id IN (1, 2, 3);

-- Reject invalid transaction
UPDATE staging_transactions
SET status = 'rejected'
WHERE id = 5;
```

## Parser Accuracy Tips

### What Works Well

✅ **Standard bank formats** with clear columns
✅ **Text-based PDFs** (not scanned images)
✅ **Consistent date formats** throughout statement
✅ **Clear amount columns** with currency symbols
✅ **Multi-line descriptions** that wrap logically

### Common Challenges

⚠️ **Scanned/image PDFs** - No text layer, requires OCR
⚠️ **Complex layouts** - Multiple tables, mixed columns
⚠️ **Inconsistent spacing** - Variable whitespace between columns
⚠️ **Foreign characters** - Special characters in merchant names
⚠️ **Non-standard dates** - Unusual date formats

### Improving Accuracy

1. **Test with real statements** from target banks
2. **Adjust regex patterns** in `transaction_detector.py`
3. **Tune heuristics** for specific bank formats
4. **Add bank-specific parsers** for major banks (Phase 2)

## Troubleshooting

### Problem: "Only PDF files are supported"

**Solution:** Ensure file has `.pdf` extension and is a valid PDF.

### Problem: "Duplicate file hash"

**Solution:** This statement was already imported. Check `statements` table:

```sql
SELECT * FROM statements WHERE file_hash = 'abc123...';
```

To re-import, delete the old record first (cascades to transactions).

### Problem: "Failed to parse PDF"

**Possible causes:**
1. PDF is password-protected
2. PDF is scanned image (needs OCR)
3. Unusual bank format

**Solution:**
- Try removing password protection
- Use OCR tool to convert to text PDF first
- Check parser logs for specific error

### Problem: Low transaction count or missing transactions

**Causes:**
- Date pattern not recognized
- Amount format not matched
- Transactions in unexpected layout

**Solution:**
- Review PDF manually to identify date/amount formats
- Update regex patterns in `transaction_detector.py`
- Test with `examples/test_parser.py` to debug

### Problem: Incorrect amounts (negatives/positives swapped)

**Solution:**
- Some banks use different conventions for debits/credits
- Add bank-specific logic to flip signs if needed
- User can manually correct in review step

## Security Considerations

### File Upload Safety

- Validate file types (PDF only)
- Scan for malware before processing
- Limit file size (e.g., 10MB max)
- Store uploaded files temporarily, delete after processing

### Database Security

- Use environment variables for credentials (never hardcode)
- Enable SSL for PostgreSQL connections
- Restrict database user permissions appropriately
- Implement rate limiting on API endpoints

### Data Privacy

- Bank statements contain sensitive financial data
- Process locally, avoid sending to third-party APIs
- Implement user authentication and authorization
- Log access to financial data for audit trail

## Next Steps

After mastering basic usage:

1. **Integrate with Lederly frontend** - Add upload UI
2. **Build review workflow** - Let users validate/correct transactions
3. **Add confidence scoring** - Auto-approve high-confidence transactions
4. **Support more banks** - Test and optimize for top 10 banks
5. **Implement batch processing** - Upload multiple statements at once

## Support

- API Documentation: http://localhost:8000/docs
- GitHub Issues: [repository URL]
- Contact: [support email]

---

**Success Criteria:** If you can upload a PDF and get back 70%+ accurate transaction data in under 30 seconds, you're on track! The goal is to beat manual entry, not achieve perfection.
