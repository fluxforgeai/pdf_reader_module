# Bank Statement Parser API

FastAPI module for parsing PDF bank statements and extracting transactions into PostgreSQL database.

## Features

- **Layered Heuristic Parser**: Date anchor + Amount anchor + Multi-line handling
- **Preview-then-Commit Flow**: Review parsed data before database insertion
- **Single Staging Table Architecture**: Simplified with status tracking
- **70% Accuracy Target**: Good enough to beat manual entry
- **Duplicate Detection**: SHA-256 file hashing prevents re-imports

## Architecture

### Core Components

1. **Transaction Detector** (`src/parsers/transaction_detector.py`)
   - Date pattern recognition (MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD)
   - Currency amount extraction (handles $, -, decimals, commas)
   - Multi-line transaction handling
   - Statement date extraction from PDF header

2. **FastAPI Endpoints** (`src/api/endpoints.py`)
   - `POST /api/statements/parse` - Parse PDF, return JSON preview
   - `POST /api/statements/confirm` - Insert approved transactions to DB
   - `GET /api/statements/health` - Health check

3. **Database Models** (`src/db/models.py`)
   - `statements` - Tracks uploaded PDFs with metadata
   - `staging_transactions` - Holds parsed transactions with status

### Database Schema

```sql
-- statements table
CREATE TABLE statements (
    id SERIAL PRIMARY KEY,
    tax_entity_id INTEGER NOT NULL,
    bank_name VARCHAR(255) NOT NULL,
    statement_date VARCHAR(50),
    file_hash VARCHAR(64) UNIQUE,
    transaction_count INTEGER DEFAULT 0,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- staging_transactions table
CREATE TABLE staging_transactions (
    id SERIAL PRIMARY KEY,
    statement_id INTEGER NOT NULL REFERENCES statements(id),
    tax_entity_id INTEGER NOT NULL,
    date VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    amount FLOAT NOT NULL,
    currency_code VARCHAR(3),
    status VARCHAR(50) DEFAULT 'pending_review',
    line_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection string
```

### 3. Initialize Database

```bash
python -m src.db.init_db
```

### 4. Run API Server

```bash
python -m src.main
# Or with uvicorn:
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test API

```bash
# Health check
curl http://localhost:8000/api/statements/health

# Parse PDF (preview)
curl -X POST http://localhost:8000/api/statements/parse \
  -F "file=@statement.pdf" \
  -F "bank_name=Wells Fargo"

# Confirm and insert to DB
curl -X POST http://localhost:8000/api/statements/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "bank_name": "Wells Fargo",
    "statement_date": "01/31/2024",
    "tax_entity_id": 1,
    "transactions": [...]
  }'
```

## Project Structure

```
.
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py          # FastAPI routes
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── transaction_detector.py  # Core parsing logic
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic models
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py         # SQLAlchemy setup
│   │   ├── models.py             # ORM models
│   │   ├── operations.py         # DB operations
│   │   └── init_db.py           # Database initialization
│   └── main.py                   # FastAPI application
├── migrations/
│   └── 001_create_statements_tables.sql
├── requirements.txt
├── .env.example
└── README.md
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Workflow

1. **Upload PDF** → `POST /api/statements/parse`
   - User uploads PDF + provides bank_name
   - Parser extracts transactions
   - Returns JSON preview with transaction count, date range, amounts

2. **Review Preview**
   - Frontend displays parsed transactions
   - User validates/corrects data
   - User can edit descriptions, amounts, dates

3. **Confirm** → `POST /api/statements/confirm`
   - User approves data
   - API inserts to `statements` + `staging_transactions` tables
   - Transactions linked via `statement_id`
   - Currency inferred from `tax_entities.currency_code`

4. **Validation** (Future)
   - Review UI to mark transactions as `validated` or `rejected`
   - Bulk approve high-confidence transactions
   - Manual correction workflow for low-confidence items

## Parser Algorithm

### Transaction Detection Heuristics

1. **Date Anchor**: Line starts with date pattern → new transaction
2. **Amount Anchor**: Line must contain currency amount
3. **Complete Pattern**: Valid transaction = Date AND Description AND Amount
4. **Multi-line Handling**:
   - Line with amount but no date → continuation with amount update
   - Line with neither → append to description if indented/short

### Supported Date Formats

- `MM/DD/YYYY` or `DD/MM/YYYY` (e.g., 01/15/2024)
- `MM-DD-YYYY` or `DD-MM-YYYY` (e.g., 01-15-2024)
- `YYYY-MM-DD` (e.g., 2024-01-15)
- `DD.MM.YYYY` (e.g., 15.01.2024)
- `Mon DD, YYYY` (e.g., Jan 15, 2024)

### Supported Amount Formats

- `$1,234.56` or `-$1,234.56`
- `1,234.56$` or `-1,234.56$`
- `1,234.56` (no symbol)
- `(1,234.56)` (accounting negative)
- Supports: $, €, £, ¥

## Success Criteria

✅ **70% parsing accuracy** - Good enough to beat manual entry
✅ **Preview before commit** - User trust and control
✅ **Duplicate prevention** - File hash checking
✅ **Bulk transaction support** - Hundreds of transactions per statement
✅ **Multi-line handling** - Wrapped descriptions

## Future Enhancements (Phase 2)

- Confidence scoring (0.0-1.0) for auto-approval
- Fuzzy bank name matching
- Pre-flight validation checks
- AWS Textract/Google Document AI fallback for scanned PDFs
- Account number extraction and auto-matching
- Batch upload support
- Review UI/UX workflow
- Parser versioning and reprocessing

## Troubleshooting

### Common Issues

1. **"Only PDF files are supported"**
   - Ensure file has .pdf extension
   - Check file is not corrupted

2. **"Duplicate file hash"**
   - Statement already imported
   - Check `statements` table for existing record

3. **"Failed to parse PDF"**
   - PDF might be scanned image (needs OCR)
   - PDF might be password-protected
   - Try different bank statement format

4. **Low parsing accuracy**
   - Some bank formats may need pattern tuning
   - Check `transaction_detector.py` regex patterns
   - Consider manual review/correction for this statement

## Development

### Running Tests

```bash
# TODO: Add pytest tests
pytest tests/
```

### Database Migrations

To run raw SQL migration:

```bash
psql -U username -d lederly -f migrations/001_create_statements_tables.sql
```

Or use SQLAlchemy:

```bash
python -m src.db.init_db
```

## License

MIT

## Support

For issues or questions, contact the development team or open an issue in the repository.
