-- Migration: 001_initial_schema.sql
-- Description: Initial database schema setup
-- Date: 2024-01-XX

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS bank_emails CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Drop existing functions and triggers
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS get_monthly_spending(TEXT) CASCADE;

-- Drop existing views
DROP VIEW IF EXISTS transaction_summary CASCADE;

-- Create categories table first (referenced by transactions)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#007bff',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create bank_emails table
CREATE TABLE bank_emails (
    id SERIAL PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    email_date TIMESTAMPTZ NOT NULL,
    sender_email TEXT,
    subject TEXT,
    body TEXT,
    imap_server TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create transactions table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    merchant_name TEXT NOT NULL,
    transactiontype VARCHAR(20) NOT NULL CHECK (transactiontype IN ('debit', 'credit', 'upi', 'credit_card', 'debit_card', 'imps', 'neft', 'emi')),
    category_id INTEGER REFERENCES categories(id),
    category VARCHAR(50) DEFAULT 'unknown',
    subject TEXT,
    imap_server TEXT,
    message_id TEXT NOT NULL UNIQUE,
    currency VARCHAR(3) DEFAULT 'INR',
    account_number TEXT,
    card_number TEXT,
    transaction_id TEXT,
    remarks TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_bank_emails_date ON bank_emails(email_date);
CREATE INDEX idx_bank_emails_sender ON bank_emails(sender_email);
CREATE INDEX idx_bank_emails_message_id ON bank_emails(message_id);

CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_transactions_merchant ON transactions(merchant_name);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_type ON transactions(transactiontype);
CREATE INDEX idx_transactions_message_id ON transactions(message_id);
CREATE INDEX idx_transactions_category_id ON transactions(category_id);

-- Insert default categories
INSERT INTO categories (name, description, color) VALUES
('groceries', 'Food and grocery purchases', '#28a745'),
('utilities', 'Electricity, water, gas bills', '#17a2b8'),
('entertainment', 'Movies, concerts, entertainment', '#ffc107'),
('travel', 'Transportation, flights, hotels', '#fd7e14'),
('dining', 'Restaurants, cafes, food delivery', '#e83e8c'),
('shopping', 'Online and offline shopping', '#6f42c1'),
('health', 'Medical expenses, pharmacy', '#dc3545'),
('education', 'Courses, books, educational expenses', '#20c997'),
('transport', 'Public transport, fuel', '#6c757d'),
('finance', 'Banking, investments, loans', '#007bff'),
('unknown', 'Uncategorized transactions', '#adb5bd');

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_bank_emails_updated_at 
    BEFORE UPDATE ON bank_emails 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at 
    BEFORE UPDATE ON transactions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for transaction summary
CREATE VIEW transaction_summary AS
SELECT 
    DATE_TRUNC('month', date) as month,
    transactiontype,
    category,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM transactions 
GROUP BY DATE_TRUNC('month', date), transactiontype, category
ORDER BY month DESC, total_amount DESC;

-- Create function for monthly spending
CREATE OR REPLACE FUNCTION get_monthly_spending(year_month TEXT)
RETURNS TABLE (
    category_name VARCHAR(50),
    total_amount NUMERIC(12,2),
    transaction_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.category,
        SUM(t.amount) as total_amount,
        COUNT(*) as transaction_count
    FROM transactions t
    WHERE TO_CHAR(t.date, 'YYYY-MM') = year_month
    GROUP BY t.category
    ORDER BY total_amount DESC;
END;
$$ LANGUAGE plpgsql;
