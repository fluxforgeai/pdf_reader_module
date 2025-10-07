# Lederly Integration - Quick Reference

**8-hour implementation** | **Zero disruption** | **Production-ready**

---

## What We're Adding

✅ OCR support for Capitec Bank statements (garbled text issue solved)
✅ Heuristic transaction detection (no AI needed)
✅ Staging table for preview/validation workflow
✅ 460+ transactions tested and working

---

## Files to Copy

```bash
# From our module to Lederly
cp src/parsers/ocr_processor.py \
   /Users/johanjgenis/Projects/PersFin/backend/app/services/

cp src/parsers/transaction_detector.py \
   /Users/johanjgenis/Projects/PersFin/backend/app/services/
```

---

## Files to Modify

1. **`/PersFin/backend/nixpacks.toml`**
   - Add: `tesseract`, `poppler_utils`

2. **`/PersFin/backend/requirements.txt`**
   - Add: `pytesseract==0.3.13`, `pdf2image==1.17.0`

3. **`/PersFin/backend/app/services/statement_parser.py`**
   - Line ~220: Add OCR fallback after Tier 3
   - Import: `from backend.app.services.ocr_processor import extract_text_with_fallback`

4. **`/PersFin/backend/app/models/models.py`**
   - Add: `class StagingTransaction(Base)` after Transaction class

5. **Create Migration:**
   ```bash
   cd /PersFin/backend
   alembic revision -m "add_staging_transactions_table"
   # Edit generated file with staging table schema
   alembic upgrade head
   ```

---

## 6-Phase Execution

| Phase | Time | What |
|-------|------|------|
| 1. Environment | 30 min | Add Tesseract to Railway |
| 2. OCR Module | 2 hours | Copy + integrate OCR |
| 3. Staging Table | 1.5 hours | Migration + model |
| 4. API Endpoints | 1 hour | Preview + confirm endpoints |
| 5. Frontend | 2 hours | Preview page |
| 6. Testing | 1 hour | E2E validation |

**Total: 8 hours**

---

## Testing Commands

```bash
# Test OCR locally
cd /PersFin/backend
python -m pytest tests/test_ocr_integration.py

# Test on Railway
curl https://your-app.railway.app/api/files/debug/libraries
# Should show: tesseract_available: true

# Upload Capitec statement
curl -X POST https://your-app.railway.app/api/upload-statement \
  -F "file=@capitec_statement.pdf" \
  -F "tax_entity_id=1"
```

---

## Success Checklist

- [ ] Tesseract installed on Railway
- [ ] OCR module copied and imports working
- [ ] Migration applied (staging_transactions table exists)
- [ ] Can upload Capitec PDF
- [ ] OCR badge shows in UI
- [ ] Preview page displays transactions
- [ ] Confirm button moves to transactions table
- [ ] All 4 Capitec statements parse successfully (460 txns)

---

## Rollback

```bash
# Database
alembic downgrade -1

# Code
git revert <commit-hash>

# Feature flag (if implemented)
ENABLE_OCR=false
```

---

## Key Integration Points

**Backend:**
- `statement_parser.py` line ~220 - Add OCR tier
- `models.py` line ~73 - Add StagingTransaction
- New files: `ocr_processor.py`, `transaction_detector.py`

**Frontend:**
- New page: `/statements/preview/[id]/page.tsx`
- Update: `/statements/upload/page.tsx` - Add OCR indicator

**Database:**
- New table: `staging_transactions`
- New columns: `status`, `line_number`

---

## Contact & Support

**Detailed Plan:** `LEDERLY_INTEGRATION_PLAN.md`
**Technical Docs:** `OCR_IMPLEMENTATION_COMPLETE.md`
**Module Docs:** `README_OCR.md`

**Questions:** Check the detailed plan for answers to:
- Database schema details
- API endpoint specifications
- Frontend component structure
- Testing procedures
- Risk mitigation strategies

---

**Ready to start? Begin with Phase 1 in the detailed plan!**

🚀 **8 hours to full Capitec support**
