import re
from email import message_from_bytes
from email.policy import default
from categories import category_map
from categories import email_map
from patterns import bank_regex_patterns, select_best_pattern
import logging
from bs4 import BeautifulSoup
import pdb
import sys
from email.utils import parsedate_to_datetime
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

def cleanup_html_content(html: str) -> str:
    """Convert HTML to clean plain text."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")
    return ' '.join(text.split())

def decode_email_body(raw_email_bytes):
    """Decode the body of an email from raw bytes, handling HTML and plain text."""
    # Ensure input is bytes
    if isinstance(raw_email_bytes, str):
        raw_email_bytes = raw_email_bytes.encode('utf-8', errors='replace')

    # Parse email using the standard library
    msg = message_from_bytes(raw_email_bytes, policy=default)

    body = None
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            #print("DEBUG content_type:", content_type, file=sys.__stdout__)
            if content_type.startswith("multipart/"):
                continue
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'

            if content_type == "text/plain" and payload:
                body = payload.decode(charset, errors="replace")
            elif content_type == "multipart/alternative" and payload:
                body = payload.decode(charset, errors="replace")  
            elif content_type == "text/html" and payload:
                html_body = payload.decode(charset, errors="replace")
                body = cleanup_html_content(html_body)
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        body = payload.decode(charset, errors="replace")
        body = cleanup_html_content(body)

    return body or ""

def is_transaction_email(email_body: str) -> bool:
    """Return True if the email body looks like a transaction, False otherwise."""
    keywords = [
        "transaction", "debited", "credited", "payment", "spent", "withdrawn", "IMPS", "NEFT", "UPI", "Credit Card", "debit card", "amount", "Rs.", "INR", "₹", "amount debited"
    ]
    return any(kw.lower() in email_body.lower() for kw in keywords)

def should_skip_email(subject: str, body: str) -> bool:
    """Return True if email should be skipped (non-transactional notifications)."""
    text = f"{subject} {body}".lower()
    
    # Skip stock market related emails
    stock_keywords = [
        "trades executed", "nse", "bse", "stock exchange", "equity", "portfolio update",
        "contract note", "securities", "dividend", "board meeting", "annual report",
        "quarterly results", "shareholder", "ipo", "fpo", "rights issue"
    ]
    
    # Skip promotional/marketing emails (but allow transaction emails with offers)
    promo_keywords = [
        "limited time offer", "special offer", "campaign", 
        "promotion", "deal", "discount", "cashback", "reward", "bonus", "gift"
        # Removed "exclusive offer" as it appears in legitimate transaction emails
    ]
    
    # Skip system notifications (but allow transaction notifications)
    system_keywords = [
        "login", "verification", "security", "maintenance",
        "server", "update", "alert", "reminder"
        # Removed "password" and "otp" as they appear in legitimate transaction emails
    ]
    
    # Skip dividend and corporate action emails
    corporate_keywords = [
        "dividend", "bonus", "split", "merger", "acquisition", "delisting",
        "corporate action", "board meeting", "agm", "egm"
    ]
    
    skip_keywords = stock_keywords + promo_keywords + system_keywords + corporate_keywords
    
    # Whitelist: if it's clearly a transaction, don't skip
    if "credit card" in text and "transaction" in text:
        return False
    
    return any(keyword in text for keyword in skip_keywords)

def extract_transaction_data(email_body: str, subject: str = "") -> dict:
    """Extract transaction data from an email body using the best matching pattern."""
    # Filter out non-transactional emails
    #if "ICICI" in subject.upper():
    #pdb.Pdb(stdout=sys.stdout).set_trace()

    if not is_transaction_email(email_body):
        logger.info("Email skipped as non-transactional.")
        return None
    
    # Skip specific types of non-transactional emails
    if should_skip_email(subject, email_body):
        logger.info(f"Email skipped as non-transactional notification: {subject}")
        return None
    # Try all patterns and select the best match
    pattern_name, match = select_best_pattern(email_body)
    if not match:
        logger.debug("No pattern matched for email body. Logging for review.")
        with open("unmatched_emails.txt", "a", encoding="utf-8") as f:
            f.write(email_body + "\n" + "="*80 + "\n")
        return None
    data = {}
    fields = bank_regex_patterns[pattern_name]["fields"]
    for idx, field in enumerate(fields):
        try:
            data[field] = match.group(idx + 1)
        except Exception:
            data[field] = ""
    # Add static fields from pattern definition
    for k, v in bank_regex_patterns[pattern_name].items():
        if k not in ("pattern", "fields"):
            data[k] = v
    # Post-process amount
    if "amount" in data:
        try:
            data["amount"] = float(str(data["amount"]).replace(",", ""))
        except Exception:
            pass
    # Post-process transactiontype based on keywords if not set or unknown
    txn_type = data.get("transactiontype", "").lower()
    body_lower = email_body.lower()
    if txn_type in ("", "unknown"):
        if "spent" in body_lower or "debited" in body_lower:
            data["transactiontype"] = "debit"
        elif "credited" in body_lower:
            data["transactiontype"] = "credit"
    
    # Normalize transaction types to our standard format
    if "transactiontype" in data:
        txn_type = data["transactiontype"].lower()
        if "upi" in txn_type:
            data["transactiontype"] = "upi"
        elif "credit card" in txn_type or "creditcard" in txn_type:
            data["transactiontype"] = "debit"  # Credit card transactions are typically debits (spending)
        elif "debit" in txn_type:
            data["transactiontype"] = "debit"
        elif "credit" in txn_type and "card" not in txn_type:
            data["transactiontype"] = "credit"
        else:
            # Default to debit for spending transactions
            data["transactiontype"] = "debit"
    
    # Set direction based on normalized transactiontype
    if "transactiontype" in data:
        if data["transactiontype"] in ["debit", "upi"]:
            data["direction"] = "debit"
        elif data["transactiontype"] == "credit":
            data["direction"] = "credit"
    # Post-process currency: set to 'INR' if any INR/Rs/₹ present
    currency_candidates = [str(data.get('currency', '')), email_body]
    if any(token in candidate for candidate in currency_candidates for token in ['INR', 'Rs', '₹']):
        data['currency'] = 'INR'
    #pdb.Pdb(stdout=sys.stdout).set_trace()
    return data

def clean_email_body(body):
    """Clean up email body text (stub for extensibility)."""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    cleaned_body = body.strip()  # Removes leading and trailing spaces/newlines
    cleaned_body = re.sub(r'\s+', ' ', cleaned_body)  # Replace multiple spaces or newlines with a single space
    return cleaned_body


# --- New function: parse_email_content ---
from email.header import decode_header

def parse_email_content(raw_email_bytes):
    """
    Parse an email from raw bytes and extract (subject, body, sender_email, email_timestamp).
    Decodes subject if encoded, extracts plain text body, sender email, and timestamp.
    """
    #pdb.Pdb(stdout=sys.__stdout__).set_trace()
    # Parse email using the standard library
    msg = message_from_bytes(raw_email_bytes, policy=default)

    # Extract and decode subject
    subject_header = msg.get("Subject", "")
    decoded_subject = ""
    if subject_header:
        dh = decode_header(subject_header)
        parts = []
        for part, enc in dh:
            if isinstance(part, bytes):
                try:
                    part_decoded = part.decode(enc or "utf-8", errors="replace")
                except Exception:
                    part_decoded = part.decode("utf-8", errors="replace")
                parts.append(part_decoded)
            else:
                parts.append(part)
        decoded_subject = ''.join(parts)
    else:
        decoded_subject = ""

    # Extract sender email from "From" header
    from_header = msg.get("From", "")
    sender_email = ""
    import re as _re
    if from_header:
        # Try to extract email address from the header
        match = _re.search(r'[\w\.-]+@[\w\.-]+', from_header)
        if match:
            sender_email = match.group(0)
        else:
            sender_email = from_header.strip()
    else:
        sender_email = ""

    # Extract email timestamp with fallback to Received header
    ist = pytz.timezone('Asia/Kolkata')
    email_timestamp = None

    # First try Date header
    date_str = msg.get("Date")
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                email_timestamp = dt.astimezone(ist)
        except Exception as e:
            logger.warning(f"Failed to parse Date header: {date_str} - {e}")

    # Fallback to last Received header if Date header is missing or unparsable
    if email_timestamp is None:
        received_headers = msg.get_all("Received", [])
        if received_headers:
            try:
                last_part = received_headers[-1].rsplit(";", 1)[-1].strip()
                dt = parsedate_to_datetime(last_part)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                email_timestamp = dt.astimezone(ist)
                logger.info("Using Received header fallback for timestamp.")
            except Exception as e:
                logger.warning(f"Failed to parse Received header fallback: {last_part} - {e}")

    #pdb.Pdb(stdout=sys.__stdout__).set_trace()


    # Extract body using decode_email_body  
    body = decode_email_body(raw_email_bytes)
    logger.info(f"Date: {email_timestamp}")


    return (decoded_subject, body, sender_email, email_timestamp)