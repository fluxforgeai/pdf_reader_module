-- Migration: Create statements and staging_transactions tables
-- Description: Implements single staging table architecture with status tracking

-- Create statements table
CREATE TABLE IF NOT EXISTS statements (
    id SERIAL PRIMARY KEY,
    tax_entity_id INTEGER NOT NULL,
    bank_name VARCHAR(255) NOT NULL,
    statement_date VARCHAR(50),
    file_hash VARCHAR(64) UNIQUE,
    transaction_count INTEGER DEFAULT 0,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for common queries
    CONSTRAINT statements_file_hash_unique UNIQUE (file_hash)
);

CREATE INDEX idx_statements_tax_entity ON statements(tax_entity_id);
CREATE INDEX idx_statements_file_hash ON statements(file_hash);
CREATE INDEX idx_statements_imported_at ON statements(imported_at);


-- Create staging_transactions table
CREATE TABLE IF NOT EXISTS staging_transactions (
    id SERIAL PRIMARY KEY,
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    tax_entity_id INTEGER NOT NULL,
    date VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    amount FLOAT NOT NULL,
    currency_code VARCHAR(3),
    status VARCHAR(50) DEFAULT 'pending_review',
    line_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Add check constraint for valid status values
    CONSTRAINT valid_status CHECK (status IN ('pending_review', 'validated', 'rejected'))
);

-- Indexes for efficient querying
CREATE INDEX idx_staging_statement ON staging_transactions(statement_id);
CREATE INDEX idx_staging_tax_entity ON staging_transactions(tax_entity_id);
CREATE INDEX idx_staging_status ON staging_transactions(status);
CREATE INDEX idx_staging_date ON staging_transactions(date);


-- Add comments for documentation
COMMENT ON TABLE statements IS 'Tracks uploaded bank statement PDFs with metadata';
COMMENT ON TABLE staging_transactions IS 'Holds parsed transactions pending review and validation';

COMMENT ON COLUMN statements.file_hash IS 'SHA-256 hash for duplicate detection';
COMMENT ON COLUMN statements.transaction_count IS 'Total number of transactions parsed from statement';
COMMENT ON COLUMN staging_transactions.status IS 'Workflow status: pending_review, validated, or rejected';
COMMENT ON COLUMN staging_transactions.line_number IS 'Original line number in PDF for traceability';
