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
from flask import Flask, jsonify
from flask import render_template
import logging
import sys
import pdb
from email import policy
from email.parser import BytesParser

# Keywords to skip
SKIP_CATEGORIES = ["promotions", "dmat", "login","OTP"]

# Set up logging
logging.basicConfig(
    level=logging.ERROR,  # Change to ERROR if you want less verbosity
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to the console
        logging.FileHandler("debug.log")  # Logs to a file named debug.log
    ]
)

# Logging decorator for phases


app = Flask(__name__)

# Load credentials from .env file
load_dotenv()
EMAIL = os.getenv("YAHOO_EMAIL")
PASSWORD = os.getenv("YAHOO_APP_PASSWORD")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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
    for sender, addresses in email_map.items():
        if email_id.lower() in [addr.lower() for addr in addresses]:
            return sender
    return "unknown"

def get_category_from_subject(subject, category_map):
    subject_lower = subject.lower()
    for category, keywords in category_map.items():
        for keyword in keywords:
            if keyword.lower() in subject_lower:
                return category
    return "others"

def save_email_to_file(subject, body, max_length=2000):
    """Save email subject and truncated body to a text file."""
    truncated_body = body[:max_length] if len(body) > max_length else body
    with open("emails.txt", "a") as f:
        f.write(f"Subject: {subject}\n")
        f.write(f"Body: {truncated_body}\n")
        f.write("-" * 80 + "\n")

    print(f"Saving email: {subject}")

def parse_email_content(raw_bytes):
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    # Extract and decode subject
    subject_raw = msg['Subject'] or ''
    subject, encoding = decode_header(subject_raw)[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or 'utf-8', errors='ignore')


    # Extract sender email
    sender = msg['From'] or ''
    sender_email = ''
    if sender:
        # Parse email address from sender string
        from email.utils import parseaddr
        sender_email = parseaddr(sender)[1]

    # Extract plain text body, fallback to html if needed
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
    # Inline HTML with formatted <script> and <pre> as requested
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Email Handler</title>
</head>
<body>
    <script>
        // Fetch emails from the server and display status
        function fetchEmails() {
            fetch('/fetch-emails')
                .then(response => response.json())
                .then(data => {
                    document.getElementById("result").innerText =
                        `Inserted: ${data.inserted} emails\\nMessage: ${data.message}\\nStart Date: ${data.start_date}\\nLast Email Timestamp: ${data.last_timestamp}`;
                })
                .catch(() => {
                    document.getElementById("result").innerText = 'Error fetching emails.';
                });
        }

        // Clean up emails on the server and display status
        function cleanupEmails() {
            fetch('/cleanup-emails')
                .then(response => response.json())
                .then(data => {
                    document.getElementById("result").innerText =
                        `Deleted: ${data.deleted} emails\\nMessage: ${data.message}`;
                })
                .catch(() => {
                    document.getElementById("result").innerText = 'Error cleaning up emails.';
                });
        }

        // Confirm before deleting a transaction
        function confirmDelete() {
            return confirm("Are you sure you want to delete this transaction?");
        }

        // Toggle sorting for table columns (ascending/descending)
        let sortAscending = true;
        function toggleSort(header) {
            sortAscending = !sortAscending;
            console.log(`Sorting by ${header} in ${sortAscending ? 'ASC' : 'DESC'} order`);
            // Add logic here to sort your table data accordingly
        }

        // Update pagination UI (disable previous/next buttons as needed)
        function updatePagination(page, totalPages) {
            let prevButton = document.getElementById("prev-button");
            let nextButton = document.getElementById("next-button");

            prevButton.disabled = page <= 1;
            nextButton.disabled = page >= totalPages;

            document.getElementById("page-number").innerText = `Page ${page} of ${totalPages}`;
        }
    </script>

    <button onclick="fetchEmails()">Fetch Emails</button>
    <button onclick="cleanupEmails()">Cleanup Emails</button>
    <pre id="result"></pre>
</body>
</html>
'''

@app.route('/status', methods=['GET'])
def status_page():
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

@app.route('/fetch-emails', methods=['GET'])
#@log_phase("Phase 2: Fetch Emails")
def fetch_emails():
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
        three_days_ago = datetime.now() - timedelta(days=1)
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
                            continue  # Skip the email if it doesn't match the pattern

                        if sender in ("demat"):
                            continue

                        data = extract_transaction_data(body)

                        # Skip if data is None or incomplete
                        if not is_valid_transaction(data):
                            logger.debug("Skipping insert due to validation failure.")
                            continue

                        logger.debug(data)
                        insert_transaction_if_valid(data, cursor, conn, subject, imap_server)
                        inserted_count += 1  # Increment only after successful insert
            except Exception as e:
                logger.error(f"Error processing mail id {mail_id}: {e}", exc_info=True)
                continue

        cursor.close()
        db_pool.putconn(conn)

        # Logout from IMAP server
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


@app.route('/cleanup-emails', methods=['GET'])
def cleanup_emails():
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
from flask import request

@app.route('/transactions', methods=['GET'])
def transactions_page():
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Change this to adjust the number of transactions per page
        offset = (page - 1) * per_page

        # Fetch categories for filtering
        cursor.execute("SELECT DISTINCT category FROM transactions")
        categories = [row[0] for row in cursor.fetchall()]

        # Get filter from query string
        category_filter = request.args.get('category', '')

        # Build query based on filter and pagination
        if category_filter:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM transactions
                WHERE date >= %s AND category = %s
                ORDER BY date DESC
                LIMIT %s OFFSET %s
            """, (thirty_days_ago, category_filter, per_page, offset))
        else:
            cursor.execute("""
                SELECT date, amount, merchant_name, transactiontype, category
                FROM transactions
                WHERE date >= %s
                ORDER BY date DESC
                LIMIT %s OFFSET %s
            """, (thirty_days_ago, per_page, offset))
        transactions = cursor.fetchall()
        cursor.close()
        db_pool.putconn(conn)

        # Format date to MM-DD-YYYY
        formatted_transactions = []
        for txn in transactions:
            formatted_transactions.append({
                "date": txn[0].strftime("%m-%d-%Y") if txn[0] else "",
                "amount": txn[1],
                "merchant_name": txn[2],
                "transactiontype": txn[3],
                "category": txn[4]
            })

        # Get the total count of transactions for pagination
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE date >= %s", (thirty_days_ago,))
        total_transactions = cursor.fetchone()[0]
        total_pages = (total_transactions + per_page - 1) // per_page  # Calculate the total number of pages
        cursor.close()

        return render_template("transactions.html",
                               transactions=formatted_transactions,
                               categories=categories,
                               page=page,
                               total_pages=total_pages)
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return jsonify({"error": "Failed to fetch transactions"}), 500



# parse_email and all direct parsing logic have been replaced by extract_email_info from maildata_extract.py


# Insert transaction to DB with decorator
#@log_phase("Phase 4: Insert into DB")
def insert_transaction_to_db(data, cursor, subject, conn, imapserver):
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