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

Edit `config.yaml` with your email and database credentials:

```yaml
email:
  address: "your_email@example.com"
  password: "your_app_password"
  imap_server: "imap.mail.yahoo.com"
database:
  host: "localhost"
  port: 5432
  dbname: "emaildb"
  user: "bankuser"
  password: "bankpass"
app:
  debug: true
  host: "0.0.0.0"
  port: 5000
```

4. **Run the app**

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
