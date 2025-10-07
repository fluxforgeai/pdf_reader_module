# Quick Start - Bank Statement Parser

Get up and running in 5 minutes!

## Prerequisites

- ✅ Python 3.8+
- ✅ PostgreSQL database
- ✅ PDF bank statement to test

## Installation Steps

### 1. Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

### 2. Configure Database (1 min)

```bash
# Copy template
cp .env.example .env

# Edit .env with your database URL
# Example: DATABASE_URL=postgresql://user:password@localhost:5432/lederly
```

### 3. Initialize Database (30 sec)

```bash
python -m src.db.init_db
```

Expected output:
```
Initializing database...
✓ Database tables created successfully
  - statements
  - staging_transactions
```

### 4. Start API Server (30 sec)

```bash
python -m src.main
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Test API (2 min)

Open browser: `http://localhost:8000/docs`

**Try the `/api/statements/parse` endpoint:**

1. Click "Try it out"
2. Upload a PDF bank statement
3. Enter bank name (e.g., "Wells Fargo")
4. Click "Execute"
5. Review parsed transactions in response

**Expected response:**
```json
{
  "bank_name": "Wells Fargo",
  "statement_date": "01/31/2024",
  "transaction_count": 47,
  "total_amount": 12450.75,
  "transactions": [...]
}
```

## Next Steps

### Test with cURL

```bash
# Health check
curl http://localhost:8000/api/statements/health

# Parse PDF
curl -X POST http://localhost:8000/api/statements/parse \
  -F "file=@your-statement.pdf" \
  -F "bank_name=Your Bank"
```

### Test with Test Scripts

```bash
# Direct parser test
python examples/test_parser.py your-statement.pdf "Bank Name"

# API test
./examples/test_api.sh your-statement.pdf
```

### Query Database

```sql
-- View statements
SELECT * FROM statements ORDER BY imported_at DESC;

-- View transactions
SELECT * FROM staging_transactions
WHERE statement_id = 1
ORDER BY line_number;
```

## Troubleshooting

### Issue: "No module named 'pdfplumber'"

**Fix:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "could not connect to server"

**Fix:** Check PostgreSQL is running and .env is correct
```bash
# Test connection
psql $DATABASE_URL
```

### Issue: "Failed to parse PDF"

**Check:**
- Is it a text-based PDF (not scanned)?
- Is it password-protected?
- Try with a different statement

### Issue: "Port 8000 already in use"

**Fix:** Kill existing process or use different port
```bash
# Use different port
uvicorn src.main:app --port 8001

# Or kill existing
lsof -ti:8000 | xargs kill
```

## Success Checklist

- [ ] Dependencies installed
- [ ] Database configured and initialized
- [ ] API server running
- [ ] Health check returns "ok"
- [ ] Successfully parsed a test PDF
- [ ] Transactions visible in database

## Documentation

- **Full README:** `README.md`
- **Detailed Guide:** `docs/USAGE_GUIDE.md`
- **Implementation:** `docs/IMPLEMENTATION_SUMMARY.md`
- **API Docs:** http://localhost:8000/docs

## Getting Help

If stuck:

1. Check error messages in terminal
2. Review `docs/USAGE_GUIDE.md` troubleshooting section
3. Check database connection with `psql`
4. Test parser directly with `examples/test_parser.py`

## What You Built

✅ PDF bank statement parser with 70% accuracy target
✅ FastAPI REST API with preview-then-commit flow
✅ PostgreSQL database with staging table
✅ Duplicate detection via file hashing
✅ Multi-line transaction handling
✅ Currency inference from tax entities

**Time investment:** 5 minutes to get running, hours saved on data entry! 🚀
