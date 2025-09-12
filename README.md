# Email Finance Manager

A modular finance manager that extracts and manages transaction data from your email inbox.

## Features
- Fetches and parses banking/transaction emails
- Categorizes and stores transactions in PostgreSQL
- Web UI for fetching, viewing, and cleaning up transactions
- Modular, extensible, and production-ready

## Requirements
- Python 3.8+
- PostgreSQL
- Docker (optional, for containerized deployment)

## Setup

1. **Clone the repository**

```bash
git clone <repo-url>
cd email_financemanager
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure the application**

Create a `.env` file in the project root with your credentials:

```bash
# Copy the example file
cp env.example .env

# Edit .env with your actual credentials
nano .env
```

Required environment variables:
- `YAHOO_EMAIL`: Your email address
- `YAHOO_APP_PASSWORD`: Your email app password
- `IMAP_SERVER`: IMAP server (default: imap.mail.yahoo.com)
- `POSTGRES_HOST`: Database host
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password
- `ADMIN_TOKEN`: Secure token for admin operations

4. **Set up the database**

```bash
# Run the database setup script
python setup_database.py
```

This will:
- Create the database if it doesn't exist
- Set up all tables, indexes, and constraints
- Insert default categories

**Note:** If you have existing data in the `debit_transactions` table, run the migration:

```bash
# When your database is accessible, run:
python run_migration.py
```

This will migrate your existing transaction data to the new schema.

5. **Run the app**

```bash
python app.py
```

Or use Docker Compose:

```bash
docker compose up --build
```

5. **Access the UI**

Visit [http://localhost:5000](http://localhost:5000) in your browser.

## Project Structure

- `app.py` - Main Flask app and routes
- `config_loader.py` - Loads YAML config
- `db.py` - Database connection pooling
- `email_fetcher.py` - IMAP/email logic
- `extract_mail_data.py`, `handlers.py`, `patterns.py`, `categories.py` - Parsing and categorization
- `templates/` - HTML templates
- `static/` - Static files (JS, CSS)

## Contributing
Pull requests and issues are welcome!

## License
MIT
