from unicodedata import category
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from config_loader import Config
from db import get_cursor
from email_fetcher import connect_to_imap, fetch_emails
from categories import category_map, email_map
from extract_mail_data import extract_transaction_data, parse_email_content
from handlers import handle_upi_email
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import time
import functools
import re
import hashlib
import sys, pdb 
import db

def process_transaction_email(subject, body, sender_email, email_date_tms,cursor):
    """
    Process a transaction email and insert into the transactions table.
    Normalizes and assigns defaults to required fields.
    """
    #pdb.Pdb(stdout=sys.__stdout__).set_trace()

    txn_data = extract_transaction_data(body)

    # ✅ make sure we have a dictionary
    if not isinstance(txn_data, dict):
       logger.warning("No transaction data extracted; skipping this email.")
       return False

    # Assign defaults and normalize fields
    required_keys = ["imap_server", "merchant_name", "transactiontype", "message_id"]
    # Set default values if missing
    for key in required_keys:
        if key not in txn_data or txn_data[key] in [None, ""]:
            if key == "imap_server":
                txn_data[key] = IMAP_SERVER if 'IMAP_SERVER' in globals() else ""
            elif key == "merchant_name":
                txn_data[key] = "unknown"
            elif key == "transactiontype":
                txn_data[key] = "debit"
            elif key == "message_id":
                # Generate a message_id if not present (use subject, email_timestamp, merchant_name)
                subject = txn_data.get("subject", "")
                email_timestamp = txn_data.get("email_timestamp", "")
                merchant_name = txn_data.get("merchant_name", "")
                unique_str = f"{subject}{email_timestamp}{merchant_name}"
                txn_data[key] = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()

    #pdb.Pdb(stdout=sys.__stdout__).set_trace()
    # Normalize transactiontype
    txn_data["transactiontype"] = normalize_transaction_type(txn_data.get("transactiontype"))

    # Ensure email_timestamp is set (default to now if missing)
    if not txn_data.get("email_timestamp"):
        txn_data["email_timestamp"] = email_date_tms

    # Log warnings for missing fields before validation
    missing_fields = [k for k in required_keys if not txn_data.get(k)]
    if missing_fields:
        logger.warning(f"Transaction missing fields {missing_fields}: {txn_data}")
    #if not is_valid_transaction(txn_data):
    #    logger.warning(f"Transaction missing critical fields or invalid: {txn_data}")
        return False
    inserted = insert_transaction_to_db(txn_data, cursor)
    if inserted:
        logger.info(f"Transaction inserted successfully: {txn_data.get('message_id')}")
        return True
    else:
        logger.error(f"Failed to insert transaction for message_id: {txn_data.get('message_id')}")
        return False

def process_bill_email(txn_data, cursor):
    """
    Process a bill email and insert into the bills table.
    """
    # The keys and normalization logic are similar to transaction, but use insert_bill_to_db
    required_keys = ["amount", "merchant_name", "transactiontype", "category", "subject", "message_id"]
    # Add missing fields with defaults for validation
    for key in required_keys:
        if key not in txn_data:
            if key == "merchant_name":
                txn_data[key] = "unknown"
            elif key == "transactiontype":
                txn_data[key] = "debit"
            elif key == "category":
                txn_data[key] = "unknown"
            elif key == "subject":
                txn_data[key] = ""
            elif key == "message_id":
                txn_data[key] = ""
            elif key == "amount":
                txn_data[key] = 0.0
    inserted = insert_bill_to_db(txn_data, cursor)
    if inserted:
        logger.info(f"Bill inserted successfully: {txn_data.get('message_id')}")
        return True
    else:
        logger.error(f"Failed to insert bill for message_id: {txn_data.get('message_id')}")
        return False

def process_statement_email(txn_data, cursor):
    """
    Process a statement email and insert into the loans/statements table.
    """
    try:
        from db import insert_loan_to_db
        inserted = insert_loan_to_db(txn_data, cursor)
        if inserted:
            logger.info(f"Statement/loan inserted successfully: {txn_data.get('message_id')}")
            return True
        else:
            logger.error(f"Failed to insert statement/loan for message_id: {txn_data.get('message_id')}")
            return False
    except Exception as e:
        logger.error(f"Error processing statement email: {e}", exc_info=True)
        return False

def process_dividend_email(txn_data, cursor):
    """
    Process a dividend email. Placeholder for actual implementation.
    """
    logger.warning(f"Dividend email processing not implemented. txn_data: {txn_data}")
    return False

config = Config()
app_conf = config.app
app = Flask(__name__)

if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)
logger = app.logger

def retry(exceptions, tries=3, delay=2, backoff=2, logger=None):
    def deco_retry(f):
        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    if logger:
                        logger.warning(f"{e}, Retrying in {mdelay} seconds...")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

load_dotenv()

DEBUG_MODE = os.getenv("FLASK_DEBUG", "false").lower() == "true"

def get_config_value(key, default=None):
    return os.environ.get(key) or (default if default is not None else "")

EMAIL = get_config_value("YAHOO_EMAIL", config.email.get("address"))
PASSWORD = get_config_value("YAHOO_APP_PASSWORD", config.email.get("password"))
IMAP_SERVER = get_config_value("IMAP_SERVER", config.email.get("imap_server"))

DB_HOST = get_config_value("POSTGRES_HOST", config.database.get("host"))
DB_PORT = get_config_value("POSTGRES_PORT", config.database.get("port"))
DB_NAME = get_config_value("POSTGRES_DB", config.database.get("dbname"))
DB_USER = get_config_value("POSTGRES_USER", config.database.get("user"))
DB_PASS = get_config_value("POSTGRES_PASSWORD", config.database.get("password"))

CHUNK_SIZE = int(get_config_value("EMAIL_FETCH_CHUNK_SIZE", 50))
ADMIN_TOKEN = get_config_value("ADMIN_TOKEN", None)



def normalize_amount(amount):
    if isinstance(amount, str):
        try:
            amount_clean = amount.replace(',', '').strip()
            return float(amount_clean)
        except Exception:
            return None
    elif isinstance(amount, (int, float)):
        return float(amount)
    else:
        return None

def normalize_transaction_type(transaction_type_value):
    """Map various transaction type strings to one of: debit, credit, upi."""
    if not transaction_type_value:
        return "debit"
    t = str(transaction_type_value).lower()
    if "credit" in t:
        return "credit"
    if "upi" in t:
        return "upi"
    return "debit"

def insert_transaction_to_db(txn_data, cursor):
    try:
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()
        # Use a savepoint so a single bad row doesn't abort the whole batch
        try:
            cursor.execute("SAVEPOINT sp_txn")
        except Exception:
            logger.warning(f"transaction data: {txn_data}")
        cursor.execute("""
            INSERT INTO transactions (amount, merchant_name, transactiontype, category, subject, imap_server, message_id, currency, email_timestamp, card_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING
        """, (
            txn_data.get("amount"),
            txn_data.get("merchant_name"),
            txn_data.get("transactiontype"),
            txn_data.get("category"),
            txn_data.get("subject"),
            txn_data.get("imap_server"),
            txn_data.get("message_id"),
            txn_data.get("currency", "INR"),
            txn_data.get("email_timestamp"),
            txn_data.get("card_number") or "0000"
        ))
        if cursor.rowcount == 0:
            logger.warning(f"Duplicate message_id skipped: {txn_data.get('message_id')}")
            return False
        return True
    except Exception as e:
        try:
            cursor.execute("ROLLBACK TO SAVEPOINT sp_txn")
        except Exception:
            pass
        logger.error(f"Failed to insert transaction to DB: {e}", exc_info=True)
        return False


# --- Insert Bill to DB ---
def insert_bill_to_db(bill_data, cursor):
    """
    Insert a bill record into the bills table, skipping duplicates by message_id.
    Returns True if inserted, False otherwise.
    """
    required_keys = ["amount", "merchant_name", "transactiontype", "category", "subject", "message_id"]
    for key in required_keys:
        if key not in bill_data or bill_data[key] in [None, ""]:
            logger.warning(f"Invalid bill data skipped (missing {key}): {bill_data}")
            return False
    try:
        # Use a savepoint so a single bad row doesn't abort the whole batch
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()
        try:
            cursor.execute("SAVEPOINT sp_bill")
        except Exception:
            pass
        cursor.execute("""
            INSERT INTO bills (amount, merchant_name, transactiontype, category, subject, message_id, currency, email_timestamp, card_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING
        """, (
            bill_data.get("amount"),
            bill_data.get("merchant_name"),
            bill_data.get("transactiontype"),
            bill_data.get("category"),
            bill_data.get("subject"),
            bill_data.get("message_id"),
            bill_data.get("currency", "INR"),
            bill_data.get("email_timestamp"),
            bill_data.get("card_number") or "0000"
        ))
        if cursor.rowcount == 0:
            logger.warning(f"Duplicate bill message_id skipped: {bill_data.get('message_id')}")
            return False
        return True
    except Exception as e:
        try:
            cursor.execute("ROLLBACK TO SAVEPOINT sp_bill")
        except Exception:
            pass
        logger.error(f"Failed to insert bill to DB: {e}", exc_info=True)
        return False

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"result": "success"})

@app.route('/status', methods=['GET'])
def status_page():
    try:
        with get_cursor() as (cursor, conn):
            cursor.execute("SELECT COUNT(*) AS count FROM bank_emails")
            record_count = cursor.fetchone()['count']
            cursor.execute("SELECT MAX(email_date) AS newest, MIN(email_date) AS oldest FROM bank_emails")
            dates = cursor.fetchone()
            max_date = dates['newest']
            min_date = dates['oldest']
            return render_template("status.html", count=record_count, newest=max_date, oldest=min_date)
    except Exception as e:
        logger.error(f"Error fetching status: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch status"}), 500

# --- Helper functions for /fetch-emails ---

def parse_fetch_params(request):
    """
    Extracts and validates fetch parameters from the request.
    Returns a dictionary with parsed values or a Flask response for error.
    """
    params = request.get_json() if request.method == 'POST' and request.is_json else request.args
    n_days = params.get('n_days')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    parsed_start_date = parsed_end_date = None
    start_index = params.get('start_index', None)
    batch_size = params.get('batch_size', None)

    if start_index is not None:
        try:
            start_index = int(start_index)
        except Exception:
            start_index = 0
    else:
        start_index = 0
    if batch_size is not None:
        try:
            batch_size = int(batch_size)
        except Exception:
            batch_size = None

    if start_date or end_date:
        if not (start_date and end_date):
            return jsonify({"error": "Both start_date and end_date are required if filtering by date."}), 400
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"error": "Invalid date format for start_date or end_date. Use YYYY-MM-DD."}), 400
        if parsed_start_date > parsed_end_date:
            return jsonify({"error": "start_date cannot be after end_date."}), 400

    if n_days is not None:
        try:
            n_days = int(n_days)
        except Exception:
            n_days = None
    if n_days is not None and (n_days <= 0 or n_days > 90):
        return jsonify({"error": "n_days must be between 1 and 90."}), 400

    # Set default fallback for email fetching filter
    if n_days is None and (start_date is None or end_date is None):
        n_days = 30  # default to last 3 days

    # Keywords
    default_keywords = [
        "transaction", "debited", "credited", "upi", "imps", "neft",
        "credit card", "debit card", "spent", "payment", "paid"
    ]
    req_keywords = params.get('keywords')
    if isinstance(req_keywords, str):
        if req_keywords.strip().lower() in ('all', '*'):
            keywords = None  # opt-out: fetch all within date filter
        else:
            keywords = [k.strip() for k in req_keywords.split(',') if k.strip()]
    elif isinstance(req_keywords, list):
        if len(req_keywords) == 0:
            keywords = None
        else:
            keywords = [str(k).strip() for k in req_keywords if str(k).strip()]
    else:
        keywords = default_keywords

    return {
        "n_days": n_days,
        "start_date": parsed_start_date,
        "end_date": parsed_end_date,
        "start_index": start_index,
        "batch_size": batch_size,
        "keywords": keywords,
    }

def connect_imap_with_retry(imap_server):
    """
    Connects to IMAP server with retry decorator.
    Returns the IMAP connection object or a Flask response for error.
    """
    try:
        imap = retry(Exception, tries=3, delay=2, backoff=2, logger=logger)(connect_to_imap)(imap_server)
        return imap
    except Exception as e:
        logger.error(f"IMAP connection/login failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to connect/login to IMAP server."}), 502

def assign_email_category(subject, body, sender_email):
    # Remove debug statements and fix logic
    sender_email_lower = (sender_email or "").strip().lower()
    # Check sender_email against email_map for each category
    if sender_email_lower:
        # Banks
        for addr in email_map.get("banks", []):
            if sender_email_lower == addr.strip().lower():
                return "transaction"
        # Amazon
        for addr in email_map.get("amazon", []):
            if sender_email_lower == addr.strip().lower():
                return "amazon"
        # Dmat
        for addr in email_map.get("dmat", []):
            if sender_email_lower == addr.strip().lower():
                return "dmat"

    return "unknown"


def process_email_chunk(chunk, cursor):
    """
    Processes a list of raw email bytes, parses each, extracts transactions,
    normalizes fields, chooses the correct processor, and returns count processed.
    """
    from email.parser import BytesParser
    from email import policy
    count = 0

    mail_data = []
    for raw_bytes in chunk:
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
            message_id = msg.get('Message-ID')
            logger.debug(f"Using parse_email_content from: {parse_email_content}")
            try:
                subject, body, sender_email, email_date = parse_email_content(raw_bytes)
                logger.warning(f"Parsed data {subject}, {sender_email}, {email_date}")
            except Exception as e:
                raw_headers = msg.items()
                logger.warning(f"Failed to parse email content: {e}. Raw headers: {raw_headers}, Raw bytes length: {len(raw_bytes)}")
                subject = ""
                body = ""
                sender_email = ""
            
            email_category = assign_email_category(subject, body, sender_email)
            print(f"email_category: {email_category}")

            if email_category == "unknown":
                continue
            elif email_category == "transaction":
                process_transaction_email(subject, body, sender_email, email_date,cursor)
            elif email_category == "bills":
                process_bill_email(subject, body, sender_email, email_date,cursor)
            elif email_category == "statement":
                process_statement_email(cursor)
            elif email_category == "divident":
                process_dividend_email(cursor)
          
            else:  
                logger.warning(f"Failed to extract transaction data for email with Message-ID: {message_id}")
        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            continue
    return count


@app.route('/fetch-emails', methods=['GET', 'POST'])
def fetch_emails_route():
    imap_server = IMAP_SERVER
    imap = None
    try:
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()
        # 1. Parse parameters
        params_or_resp = parse_fetch_params(request)
        if isinstance(params_or_resp, tuple):  # error response from helper
            return params_or_resp
        params = params_or_resp
        n_days = params.get("n_days")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        keywords = params.get("keywords")
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()
        # 2. Connect to IMAP
        imap_or_resp = connect_imap_with_retry(imap_server)
        if isinstance(imap_or_resp, tuple):  # error response from helper
            return imap_or_resp
        imap = imap_or_resp
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()

        # 3. Fetch emails
        raw_emails = fetch_emails(
            imap,
            n_days=n_days,
            start_date=start_date,
            end_date=end_date,
            keywords=keywords,
            search_fields=["SUBJECT", "BODY"]
        )
        #pdb.Pdb(stdout=sys.__stdout__).set_trace()

        if not raw_emails:
            filter_info = f"last {n_days} days" if n_days else f"{start_date.isoformat()} to {end_date.isoformat()}" if start_date else "no filter"
            return jsonify({"saved": 0, "message": "No emails found for the given filter.", "filter": filter_info})
        count = 0
        with get_cursor() as (cursor, conn):
            for i in range(0, len(raw_emails), CHUNK_SIZE):
                chunk = raw_emails[i:i+CHUNK_SIZE]
                processed_count = process_email_chunk(chunk, cursor)
                count += processed_count
            conn.commit()
        filter_info = f"last {n_days} days" if n_days else f"{start_date.isoformat()} to {end_date.isoformat()}" if start_date else "no filter"
        logger.info(f"Saved {count} email transactions to database.")
        return jsonify({"saved": count, "message": "Email transactions saved to database", "filter": filter_info})
    except Exception as e:
        logger.error(f"Error fetching emails: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch emails"}), 500
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass


@app.route('/cleanup-emails', methods=['POST'])
def cleanup_emails():
    #token = request.headers.get('X-ADMIN-TOKEN')
    #ip_addr = request.remote_addr
    #if not ADMIN_TOKEN or token != ADMIN_TOKEN:
    #    logger.warning(f"Unauthorized attempt to cleanup emails from IP: {ip_addr}")
    #    return jsonify({"error": "Unauthorized"}), 401
    #logger.info(f"Authorized cleanup request from IP: {ip_addr}")
    try:
        with get_cursor() as (cursor, conn):
            cursor.execute("DELETE FROM transactions;")
            transactions_deleted = cursor.rowcount
            cursor.execute("DELETE FROM bills;")
            bills_deleted = cursor.rowcount
            #cursor.execute("DELETE FROM loans;")
            #loans_deleted = cursor.rowcount
            conn.commit()
            return jsonify({
                "deleted_transactions": transactions_deleted,
                "deleted_bills": bills_deleted,
                #"deleted_loans": loans_deleted,
                "message": "All emails, bills, and loans deleted from DB."
            })
    except Exception as e:
        logger.error(f"Error cleaning up emails: {e}", exc_info=True)
        return jsonify({"error": "Failed to clean up emails"}), 500
    
@app.route('/transactions', methods=['GET'])
def transactions_page():
    class TransactionObj:
        def __init__(self, data):
            self.__dict__.update(data)

    try:
        limit = request.args.get('limit', type=int) or 100
        offset = request.args.get('offset', type=int, default=0)

        # Detect JSON request
        accept = request.headers.get("Accept", "")
        use_json = request.args.get("format", "").lower() == "json" or any(
            "application/json" in part for part in accept.split(",")
        )

        with get_cursor() as (cursor, conn):
            # Fetch distinct categories
            cursor.execute("SELECT DISTINCT category FROM transactions")
            categories = [row['category'] for row in cursor.fetchall() if row['category']]

            category_filter = request.args.get('category', '')

            # Base query with LEFT JOIN to accounts table based on account_number
            base_query = """
                SELECT t.email_timestamp, t.amount, t.merchant_name, t.transactiontype,
                       t.card_number, t.category, a.account_name, a.account_type
                FROM transactions t
                LEFT JOIN accounts a ON t.card_number = a.account_number
            """
            params = []
            if category_filter:
                base_query += " WHERE t.category = %s"
                params.append(category_filter)

            base_query += " ORDER BY t.email_timestamp DESC"
            if limit is not None:
                base_query += " LIMIT %s"
                params.append(limit)
            if offset:
                base_query += " OFFSET %s"
                params.append(offset)

            cursor.execute(base_query, tuple(params))
            transactions = cursor.fetchall()

            # Ensure all fields have defaults if missing
            formatted_transactions = []
            for txn in transactions:
                txn_data = {
                    "email_timestamp": txn.get('email_timestamp'),
                    "amount": txn.get('amount', 0.0),
                    "merchant_name": txn.get('merchant_name', "unknown"),
                    "transactiontype": txn.get('transactiontype', "debit"),
                    "card_number": txn.get('card_number') if txn.get('card_number') else "-",
                    "category": txn.get('category', "unknown"),
                    "account_name": txn.get('account_name') or "-",
                    "account_type": txn.get('account_type') or "-",
                }
                formatted_transactions.append(TransactionObj(txn_data))

            if use_json:
                return jsonify([
                    {
                        "date": txn.email_timestamp.strftime("%m-%d-%Y %H:%M:%S") if txn.email_timestamp else "",
                        "amount": txn.amount,
                        "merchant_name": txn.merchant_name,
                        "transactiontype": txn.transactiontype,
                        "card_number": txn.card_number,
                        "category": txn.category,
                        "account_name": txn.account_name,
                        "account_type": txn.account_type,
                    }
                    for txn in formatted_transactions
                ])
            else:
                return render_template(
                    "transactions.html",
                    transactions=formatted_transactions,
                    categories=categories,
                    applied_filter=(category_filter or 'all')
                )

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch transactions"}), 500
    
@app.route('/bills', methods=['GET'])
def bills_page():
    class BillObj:
        def __init__(self, data):
            self.__dict__.update(data)
    try:
        with get_cursor() as (cursor, conn):
            cursor.execute("""
                SELECT email_timestamp, amount, merchant_name, transactiontype, card_number, category, subject
                FROM bills
                ORDER BY email_timestamp DESC
            """)
            bills = cursor.fetchall()
            formatted_bills = []
            for bill in bills:
                bill_data = {
                    "email_timestamp": bill.get('email_timestamp'),
                    "amount": bill.get('amount', 0.0),
                    "merchant_name": bill.get('merchant_name', "unknown"),
                    "transactiontype": bill.get('transactiontype', "debit"),
                    "card_number": bill.get('card_number') if bill.get('card_number') else "-",
                    "category": bill.get('category', "unknown"),
                    "subject": bill.get('subject', ""),
                }
                formatted_bills.append(BillObj(bill_data))
            return render_template("bills.html", bills=formatted_bills)
    except Exception as e:
        logger.error(f"Error fetching bills: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch bills"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server Error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.error(f"Unhandled Exception: {error}", exc_info=True)
    return jsonify({"error": "Unexpected server error"}), 500

# --- ACCOUNTS CRUD ---

@app.route('/accounts', methods=['GET'])
def accounts():
    accounts = db.get_all_accounts()
    return render_template('accounts.html', accounts=accounts)

@app.route('/accounts/add', methods=['POST'])
def add_account():
    data = request.form
    db.add_account(data)
    return redirect(url_for('accounts'))

@app.route('/accounts/edit/<int:account_id>', methods=['POST'])
def edit_account(account_id):
    data = request.form
    db.update_account(account_id, data)
    return redirect(url_for('accounts'))

@app.route('/accounts/delete/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    db.delete_account(account_id)
    return redirect(url_for('accounts'))

if __name__ == '__main__':
    app.run(host=app_conf.get('host', '0.0.0.0'), port=app_conf.get('port', 5050), debug=DEBUG_MODE)
