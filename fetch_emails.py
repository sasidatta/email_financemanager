import imaplib
from categories import category_map, email_map
from handlers import handle_upi_email
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from extract_mail_data import decode_email_body, extract_transaction_data
import re
import psycopg2
from psycopg2 import pool
from flask import Flask, jsonify, render_template, request
import logging
from email import policy
from email.parser import BytesParser

# Keywords to skip
SKIP_CATEGORIES = ["promotions", "dmat", "login","OTP"]

# Set up logging (single configuration)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("debug.log")
    ]
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Load credentials from .env file
load_dotenv()
EMAIL = os.getenv("YAHOO_EMAIL")
PASSWORD = os.getenv("YAHOO_APP_PASSWORD")

# Validate environment variables
required_env_vars = [EMAIL, PASSWORD, os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_USER"), os.getenv("POSTGRES_PASSWORD")]
if not all(required_env_vars):
    logger.error("Missing necessary environment variables.")
    exit(1)

# Set up PostgreSQL connection pooling
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", 5432),
    dbname=os.getenv("POSTGRES_DB", "emaildb"),
    user=os.getenv("POSTGRES_USER", "bankuser"),
    password=os.getenv("POSTGRES_PASSWORD", "bankpass")
)

def log_phase(phase_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"[{phase_name}] Start")
            try:
                result = func(*args, **kwargs)
                logger.info(f"[{phase_name}] End")
                return result
            except Exception as e:
                logger.error(f"[{phase_name}] Error: {e}")
                raise
        return wrapper
    return decorator

def get_sender_from_email(email_id, email_map):
    """Return sender name from email address using email_map."""
    for sender, addresses in email_map.items():
        if email_id.lower() in [addr.lower() for addr in addresses]:
            return sender
    return "unknown"

def get_category_from_subject(subject, category_map):
    """Return category from subject using category_map."""
    subject_lower = subject.lower()
    for category, keywords in category_map.items():
        for keyword in keywords:
            if keyword.lower() in subject_lower:
                return category
    return "others"

def save_email_to_file(subject, body, max_length=2000):
    """Save email subject and truncated body to a text file (for debugging/logging)."""
    truncated_body = body[:max_length] if len(body) > max_length else body
    with open("emails.txt", "a") as f:
        f.write(f"Subject: {subject}\n")
        f.write(f"Body: {truncated_body}\n")
        f.write("-" * 80 + "\n")
    logger.info(f"Saving email: {subject}")

def parse_email_content(raw_bytes):
    """Parse raw email bytes and extract subject, body, and sender email."""
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

#@log_phase("Phase 1: Connect to IMAP")
def connect_to_imap(server):
    imap = imaplib.IMAP4_SSL(server)
    imap.login(EMAIL, PASSWORD)
    imap.select("INBOX")
    return imap

@app.route('/')
def index():
    """Render the main index page."""
    return render_template("index.html")

@app.route('/status', methods=['GET'])
def status_page():
    """Show sync status and email DB stats."""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bank_emails")
        record_count = cursor.fetchone()[0]
        cursor.execute("SELECT MAX(email_date), MIN(email_date) FROM bank_emails")
        max_date, min_date = cursor.fetchone()
        cursor.close()
        db_pool.putconn(conn)
        return render_template("status.html", count=record_count, newest=max_date, oldest=min_date)
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({"error": "Failed to fetch status"}), 500

@app.route('/fetch-emails', methods=['GET','POST'])
def fetch_emails():
    """Fetch new emails from IMAP and insert valid transactions into the DB."""
    try:
        imap_server = "imap.mail.yahoo.com"
        # Connect to Yahoo's IMAP server
        imap = connect_to_imap(imap_server)
        # Get the most recent email_date from the database
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(email_date), '1970-01-01') FROM bank_emails")
        last_timestamp = cursor.fetchone()[0]
        cursor.close()

        # Calculate the date range for the last 0 days
        three_days_ago = datetime.now() - timedelta(days=130)
        since_date = three_days_ago.strftime("%d-%b-%Y")
    
        # Define banking-related keywords
        bank_keywords = [
            "transaction", "credited", "debited", "account", "balance",
            "payment", "received", "spent", "withdrawn", "ICICI", "SBI", "HDFC",
            "Axis", "KOTAK", "RBL", "BOB", "IDFC", "YES BANK", "UPI", "NEFT", "IMPS"
        ]
        pattern = re.compile(r"|".join(bank_keywords), re.IGNORECASE)

        # Fetch email IDs since the desired date
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

                        # Check if subject matches the banking keywords pattern
                        if not pattern.search(subject):
                            continue
                        if sender in ("demat"):
                            continue
                        data = extract_transaction_data(body)
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
        db_pool.putconn(conn)
        imap.logout()
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

@app.route('/cleanup-emails', methods=['POST'])
def cleanup_emails():
    """Delete all emails from the DB. (POST for safety)"""
    # TODO: Add authentication/authorization here for production use
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bank_emails")
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        return jsonify({"deleted": deleted_count, "message": "All emails deleted from DB."})
    except Exception as e:
        logger.error(f"Error cleaning up emails: {e}")
        return jsonify({"error": "Failed to clean up emails"}), 500

# New route: /transactions
@app.route('/transactions', methods=['GET'])
def transactions_page():
    """Show all transactions from the transactions table."""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        # Fetch all categories for filtering
        cursor.execute("SELECT DISTINCT category FROM transactions")
        categories = [row[0] for row in cursor.fetchall()]
        # Get filter from query string
        category_filter = request.args.get('category', '')
        # Build query based on filter
        if category_filter:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM transactions
                WHERE category = %s
                ORDER BY date DESC
            """, (category_filter,))
        else:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM transactions
                ORDER BY date DESC
            """)
        transactions = cursor.fetchall()
        cursor.close()
        db_pool.putconn(conn)
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

# parse_email and all direct parsing logic have been replaced by extract_email_info from maildata_extract.py

# Insert transaction to DB with decorator
#@log_phase("Phase 4: Insert into DB")
def insert_transaction_to_db(data, cursor, subject, conn, imapserver):
    """Insert a transaction into the DB, handling Yahoo and other IMAP servers."""
    try:
        if imapserver == "imap.mail.yahoo.com":
            mailid = "dattu2009@yahoo.com"
            cursor.execute(
                """INSERT INTO transactions (email_address, transactionid, amount, merchant_name, transactiontype, category, date, card_number, merchant_paymentid, currency)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (transactionid) DO NOTHING""",
                (
                    mailid, data['transactionid'], data['amount'], data['merchant_name'],
                    data['transactiontype'], data['category'], data['date'],
                    data['card_number'], data.get('merchant_paymentid', ''), data['currency']
                )
            )
        else:
            cursor.execute(
                """INSERT INTO transactions (email_id, transactionid, amount, merchant_name, transactiontype, category, date, card_number, merchant_paymentid, currency)
                   SELECT id, %s, %s, %s, %s, %s, %s, %s, %s, %s
                   FROM bank_emails
                   WHERE subject = %s
                   ON CONFLICT (transactionid) DO NOTHING""",
                (
                    data['transactionid'], data['amount'], data['merchant_name'],
                    data['transactiontype'], data['category'], data['date'],
                    data['card_number'], data.get('merchant_paymentid', ''), data['currency'], subject
                )
            )
        conn.commit()
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")
        logger.debug(f"Failing Data: {data}")
        raise

def insert_transaction_if_valid(data, cursor, conn, subject, imapserver):
    """Insert transaction if all required fields are present."""
    required_keys = ("transactionid", "amount", "merchant_name", "transactiontype", "category", "date", "card_number", "currency")
    if not data or not all(k in data for k in required_keys):
        logger.debug("Incomplete transaction data. Skipping insert.")
        return
    try:
        insert_transaction_to_db(data, cursor, subject, conn, imapserver)
    except Exception as e:
        logger.error(f"Failed to insert transaction: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True, use_reloader=False)