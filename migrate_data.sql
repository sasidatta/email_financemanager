-- Manual migration script for existing debit_transactions data
-- Run this script when your database is accessible

-- Check if old table exists and migrate data
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'debit_transactions') THEN
        -- Migrate existing data from debit_transactions to transactions
        INSERT INTO transactions (
            date,
            amount,
            merchant_name,
            transactiontype,
            category,
            currency,
            card_number,
            message_id,
            created_at
        )
        SELECT 
            COALESCE(date, CURRENT_DATE),
            amount,
            COALESCE(merchant_name, 'unknown'),
            COALESCE(transactiontype, 'debit'),
            COALESCE(category, 'unknown'),
            COALESCE(currency, 'INR'),
            card_number,
            COALESCE(message_id, transactionid),
            NOW()
        FROM debit_transactions
        ON CONFLICT (message_id) DO NOTHING;
        
        -- Log migration
        RAISE NOTICE 'Migrated % rows from debit_transactions to transactions', 
            (SELECT COUNT(*) FROM debit_transactions);
            
        -- Drop old table after successful migration
        DROP TABLE IF EXISTS debit_transactions;
        
    ELSE
        RAISE NOTICE 'No existing debit_transactions table found. Skipping migration.';
    END IF;
END $$;
