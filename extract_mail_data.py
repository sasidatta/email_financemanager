import re
from email import message_from_bytes
from email.policy import default
import sys
from bs4 import BeautifulSoup
import pdb
from categories import category_map
from categories import email_map
from cleaner_script import cleanup_html_content, verify_html_cleanup
from patterns import bank_regex_patterns, normalize_debit_transaction, select_best_pattern
import logging

logger = logging.getLogger(__name__)

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
        "transaction", "debited", "credited", "payment", "spent", "withdrawn", "IMPS", "NEFT", "UPI", "Credit Card", "debit card", "amount", "Rs.", "INR", "₹"
    ]
    return any(kw.lower() in email_body.lower() for kw in keywords)

def extract_transaction_data(email_body: str) -> dict:
    """Extract transaction data from an email body using the best matching pattern."""
    # Filter out non-transactional emails
    if not is_transaction_email(email_body):
        logger.info("Email skipped as non-transactional.")
        return None
    # Try all patterns and select the best match
    pattern_name, match = select_best_pattern(email_body)
    if not match:
        logger.warning("No pattern matched for email body. Logging for review.")
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
    # Post-process date (normalize to YYYY-MM-DD if possible)
    if "date" in data:
        try:
            # Try to parse various date formats
            import dateutil.parser
            dt = dateutil.parser.parse(data["date"], dayfirst=True, fuzzy=True)
            data["date"] = dt.strftime("%Y-%m-%d")
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
    # Optionally, set direction as well
    if "transactiontype" in data:
        if data["transactiontype"].lower().startswith("debit"):
            data["direction"] = "debit"
        elif data["transactiontype"].lower().startswith("credit"):
            data["direction"] = "credit"
    # Post-process currency: set to 'INR' if any INR/Rs/₹ present
    currency_candidates = [str(data.get('currency', '')), email_body]
    if any(x in c for c in currency_candidates for x in ['INR', 'Rs', '₹']):
        data['currency'] = 'INR'
    return data

def clean_email_body(body):
    """Clean up email body text (stub for extensibility)."""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    cleaned_body = body.strip()  # Removes leading and trailing spaces/newlines
    cleaned_body = re.sub(r'\s+', ' ', cleaned_body)  # Replace multiple spaces or newlines with a single space
    return cleaned_body

def verify_html_cleanup(cleaned_text):
    """Check if HTML tags or major HTML constructs still remain in the cleaned text."""
    if (
        re.search(r'<[^>]+>', cleaned_text)
        or "<html" in cleaned_text.lower()
        or "<!doctype" in cleaned_text.lower()
    ):
        print("WARNING: HTML cleanup incomplete - tags still present.")