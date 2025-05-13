from flask import Flask, render_template, jsonify, request
from config_loader import Config
from db import get_conn, put_conn
from email_fetcher import connect_to_imap
from extract_mail_data import decode_email_body, extract_transaction_data
from categories import category_map, email_map
from handlers import handle_upi_email
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv

# Optional: CORS and Swagger UI
try:
    from flask_cors import CORS
    from flask_swagger_ui import get_swaggerui_blueprint
    HAS_SWAGGER = True
except ImportError:
    HAS_SWAGGER = False

config = Config()
app_conf = config.app

app = Flask(__name__)

# CORS support
if HAS_SWAGGER:
    CORS(app)

# Logging with rotation
if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
logger = app.logger

# Load .env if present (for local overrides)
load_dotenv()

def get_config_value(key, default=None):
    """Get config value from environment or config.yaml (env takes precedence)."""
    return os.environ.get(key, default)

# Email/IMAP config
EMAIL = get_config_value("YAHOO_EMAIL", config.email.get("address"))
PASSWORD = get_config_value("YAHOO_APP_PASSWORD", config.email.get("password"))
IMAP_SERVER = get_config_value("IMAP_SERVER", config.email.get("imap_server"))

# DB config (if needed elsewhere)
DB_HOST = get_config_value("POSTGRES_HOST", config.database.get("host"))
DB_PORT = get_config_value("POSTGRES_PORT", config.database.get("port"))
DB_NAME = get_config_value("POSTGRES_DB", config.database.get("dbname"))
DB_USER = get_config_value("POSTGRES_USER", config.database.get("user"))
DB_PASS = get_config_value("POSTGRES_PASSWORD", config.database.get("password"))

if HAS_SWAGGER:
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.yaml'  # You should create this file for full docs
    swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={{'app_name': "Email Finance Manager"}})
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/')
def index():
    """Render the main index page."""
    return render_template("index.html")

@app.route('/health', methods=['GET'])
def health():
    """Healthcheck endpoint for Docker/monitoring."""
    return jsonify({"status": "ok"}), 200

@app.route('/test', methods=['GET'])
def test():
    """Simple test endpoint for CI/CD or smoke tests."""
    return jsonify({"result": "success"})

@app.route('/status', methods=['GET'])
def status_page():
    """Show sync status and email DB stats."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bank_emails")
        record_count = cursor.fetchone()[0]
        cursor.execute("SELECT MAX(email_date), MIN(email_date) FROM bank_emails")
        max_date, min_date = cursor.fetchone()
        cursor.close()
        return render_template("status.html", count=record_count, newest=max_date, oldest=min_date)
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({"error": "Failed to fetch status"}), 500
    finally:
        put_conn(conn)

@app.route('/fetch-emails', methods=['GET','POST'])
def fetch_emails():
    """Fetch new emails from IMAP and insert valid transactions into the DB."""
    imap_server = IMAP_SERVER
    imap = None
    conn = get_conn()
    try:
        imap = connect_to_imap(imap_server)
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(email_date), '1970-01-01') FROM bank_emails")
        last_timestamp = cursor.fetchone()[0]
        cursor.close()

        three_days_ago = datetime.now() - timedelta(days=13)
        since_date = three_days_ago.strftime("%d-%b-%Y")
        bank_keywords = [
            "transaction", "credited", "debited", "account", "balance",
            "payment", "received", "spent", "withdrawn", "ICICI", "SBI", "HDFC",
            "Axis", "KOTAK", "RBL", "BOB", "IDFC", "YES BANK", "UPI", "NEFT", "IMPS"
        ]
        pattern = re.compile(r"|".join(bank_keywords), re.IGNORECASE)

        status, messages = imap.search(None, f'(SINCE "{since_date}")')
        if status != "OK":
            logger.error("Failed to search emails.")
            return jsonify({"error": "Failed to search emails"}), 500
        mail_ids = messages[0].split()
        cursor = conn.cursor()
        inserted_count = 0
        for mail_id in mail_ids:
            try:
                status, msg_data = imap.fetch(mail_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        subject, body, sender_email = parse_email_content(response_part[1])
                        sender = get_sender_from_email(sender_email, email_map)
                        logger.debug(subject)
                        if sender in ("demat"):
                            continue
                        data = extract_transaction_data(body)
                        if not data:
                            continue
                        if not is_valid_transaction(data):
                            logger.debug("Skipping insert due to validation failure.")
                            continue
                        logger.debug(data)
                        insert_transaction_if_valid(data, cursor, conn, subject, imap_server)
                        inserted_count += 1
            except Exception as e:
                logger.error(f"Error processing mail id {mail_id}: {e}", exc_info=True)
                continue
        cursor.close()
        logger.info(f"Inserted {inserted_count} new banking-related emails into the database.")
        return jsonify({
            "inserted": inserted_count,
            "message": "Done",
            "last_timestamp": last_timestamp,
            "start_date": since_date
        })
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return jsonify({"error": "Failed to fetch emails"}), 500
    finally:
        if imap:
            imap.logout()
        put_conn(conn)

@app.route('/cleanup-emails', methods=['POST'])
def cleanup_emails():
    """Delete all emails from the DB. (POST for safety)"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bank_emails")
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        return jsonify({"deleted": deleted_count, "message": "All emails deleted from DB."})
    except Exception as e:
        logger.error(f"Error cleaning up emails: {e}")
        return jsonify({"error": "Failed to clean up emails"}), 500
    finally:
        put_conn(conn)

@app.route('/transactions', methods=['GET'])
def transactions_page():
    """Show all transactions from the debit_transactions table."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM debit_transactions")
        categories = [row[0] for row in cursor.fetchall()]
        category_filter = request.args.get('category', '')
        if category_filter:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM debit_transactions
                WHERE category = %s
                ORDER BY date DESC
            """, (category_filter,))
        else:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM debit_transactions
                ORDER BY date DESC
            """)
        transactions = cursor.fetchall()
        cursor.close()
        formatted_transactions = []
        for txn in transactions:
            formatted_transactions.append({
                "date": txn[0].strftime("%m-%d-%Y") if txn[0] else "",
                "amount": txn[1],
                "merchant_name": txn[2],
                "transactiontype": txn[3],
                "category": txn[4]
            })
        return render_template("transactions.html",
                               transactions=formatted_transactions,
                               categories=categories)
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return jsonify({"error": "Failed to fetch transactions"}), 500
    finally:
        put_conn(conn)

@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 error handler."""
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error handler."""
    logger.error(f"Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Helper functions (moved from fetch_emails.py)
def get_sender_from_email(email_id, email_map):
    """Return sender name from email address using email_map."""
    for sender, addresses in email_map.items():
        if email_id.lower() in [addr.lower() for addr in addresses]:
            return sender
    return "unknown"

def parse_email_content(raw_bytes):
    """Parse raw email bytes and extract subject, body, and sender email."""
    from email.header import decode_header
    from email import policy
    from email.parser import BytesParser
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    subject_raw = msg['Subject'] or ''
    subject, encoding = decode_header(subject_raw)[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or 'utf-8', errors='ignore')
    sender = msg['From'] or ''
    sender_email = ''
    if sender:
        from email.utils import parseaddr
        sender_email = parseaddr(sender)[1]
    body = ''
    html_body = ''
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            if content_type == 'text/plain' and payload:
                body = payload.decode(charset, errors='ignore')
                break
            elif content_type == 'text/html' and payload and not body:
                html_body = payload.decode(charset, errors='ignore')
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        body = payload.decode(charset, errors='ignore')
    if not body and html_body:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_body, "html.parser")
        body = soup.get_text()
    return subject.strip(), body.strip(), sender_email.strip()

def is_valid_transaction(data):
    """Check if transaction data contains all required fields."""
    required_keys = ("transactionid", "amount", "merchant_name", "transactiontype", "category", "date", "card_number")
    if not data:
        return False
    missing_keys = [k for k in required_keys if k not in data]
    if missing_keys:
        logger.debug(f"Incomplete transaction data. Missing keys: {missing_keys}")
        return False
    return True

def insert_transaction_to_db(data, cursor, subject, conn, imapserver):
    """Insert a transaction into the correct table (debit or credit) based on direction."""
    try:
        logger.debug(data)
        direction = data.get("direction", "debit")
        if direction == "credit":
            cursor.execute(
                """INSERT INTO credit_transactions (
                        email_address, transactionid, amount, sender_name, transactiontype, category, date, account_number, remarks, currency
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (transactionid) DO NOTHING""",
                (
                    data.get('email_address', ''),
                    data['transactionid'],
                    data['amount'],
                    data.get('sender_name', ''),
                    data.get('transactiontype', ''),
                    data.get('category', ''),
                    data.get('date', None),
                    data.get('account_number', ''),
                    data.get('remarks', ''),
                    data.get('currency', 'INR')
                )
            )
        else:
            cursor.execute(
                """INSERT INTO debit_transactions (
                        email_address, transactionid, amount, merchant_name, transactiontype, category, date, card_number, merchant_paymentid, currency
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (transactionid) DO NOTHING""",
                (
                    data.get('email_address', ''),
                    data['transactionid'],
                    data['amount'],
                    data.get('merchant_name', ''),
                    data.get('transactiontype', ''),
                    data.get('category', ''),
                    data.get('date', None),
                    data.get('card_number', ''),
                    data.get('merchant_paymentid', ''),
                    data.get('currency', 'INR')
                )
            )
        conn.commit()
        logger.debug("data inserted")
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")
        logger.debug(f"Failing Data: {data}")
        raise

def insert_transaction_if_valid(data, cursor, conn, subject, imapserver):
    """Insert transaction if all required fields are present."""
    if not data or not data.get('transactionid') or not data.get('amount'):
        logger.debug("Incomplete transaction data. Skipping insert.")
        return
    try:
        insert_transaction_to_db(data, cursor, subject, conn, imapserver)
    except Exception as e:
        logger.error(f"Failed to insert transaction: {e}")

if __name__ == '__main__':
    app.run(host=app_conf.get('host', '0.0.0.0'), port=app_conf.get('port', 5000), debug=app_conf.get('debug', True)) 