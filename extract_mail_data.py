import base64
import re
from email import message_from_bytes
from email.policy import default
import sys
from bs4 import BeautifulSoup
import pdb
from categories import category_map
from categories import email_map
from cleaner_script import cleanup_html_content
from patterns import bank_regex_patterns

def decode_email_body(raw_email_bytes):
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

def clean_email_body(body):
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    cleaned_body = body.strip()  # Removes leading and trailing spaces/newlines
    cleaned_body = re.sub(r'\s+', ' ', cleaned_body)  # Replace multiple spaces or newlines with a single space
    return cleaned_body

def extract_transaction_data(email_body):
    email_body = decode_email_body(email_body) 
    email_body = clean_email_body(email_body)
    verify_html_cleanup(email_body)
    # Define banking-related keywords
    bank_keywords = [
       "transaction", "credit card", "credited", "debited", "account", "balance",
       "payment", "received", "spent", "withdrawn", "ICICI", "SBI", "HDFC",
       "Axis", "KOTAK", "RBL", "BOB", "IDFC", "YES BANK", "UPI", "NEFT", "IMPS"
    ]
    pattern = re.compile(r"|".join(bank_keywords), re.IGNORECASE)
    # If no banking-related keywords are found, skip processing
    if not pattern.search(email_body):
        return None
    with open("dump.txt", "a", encoding="utf-8") as dump_file:
        dump_file.write(email_body + "\n" + "="*80 + "\n")
    for bank_name, data in bank_regex_patterns.items():
        match = data["pattern"].search(email_body)
        if match:
            values = match.groups()
            # Try to get amount field for currency
            amount_text = None
            if "amount" in data["fields"]:
                amount_text = values[data["fields"].index("amount")]
            currency = "INR" if amount_text and ("INR" in amount_text or "Rs" in amount_text) else "UNKNOWN"
            result = {"currency": currency}
            # Add card if present in pattern
            if "card" in data:
                result["card"] = data["card"]
            # Add all regex fields
            result.update(dict(zip(data["fields"], values)))
            # Add transactiontype and direction if present
            if "transactiontype" in data:
                result["transactiontype"] = data["transactiontype"]
            if "transaction_direction" in data:
                result["direction"] = data["transaction_direction"]
            else:
                # Fallback: guess from transactiontype
                ttype = result.get("transactiontype", "").lower()
                if "credit" in ttype:
                    result["direction"] = "credit"
                else:
                    result["direction"] = "debit"
            # Reformat date to YYYY-MM-DD if possible
            if "date" in result:
                try:
                    sep = "/" if "/" in result["date"] else "-"
                    parts = result["date"].split(sep)
                    if len(parts) == 3:
                        if len(parts[2]) == 2:
                            year = "20" + parts[2]
                        else:
                            year = parts[2]
                        # Try to detect if format is DD-MM-YYYY or YYYY-MM-DD
                        if int(parts[0]) > 31:  # year first
                            result["date"] = f"{parts[0]}-{parts[1]}-{parts[2]}"
                        else:
                            result["date"] = f"{year}-{parts[1]}-{parts[0]}"
                except Exception:
                    pass  # Leave original date if parsing fails
            import logging
            logging.basicConfig(level=logging.INFO)
            for key, value in result.items():
                logging.info(f"{key}: {value}")
            if "amount" in result:
                result["amount"] = float(result["amount"].replace(",", ""))
            # Generate a transaction ID if not already present
            if "transactionid" not in result or not result["transactionid"]:
                result["transactionid"] = f"{result.get('card_number', '')}_{result.get('amount', '')}_{result.get('date', '')}"
            # Add transactiontype if missing
            if "transactiontype" not in result or not result["transactiontype"]:
                if "credit" in result.get("card", "").lower():
                    result["transactiontype"] = "credit card"
                elif "debit" in result.get("card", "").lower():
                    result["transactiontype"] = "debit card"
                else:
                    result["transactiontype"] = "unknown"
            # Set category based on merchant_name or other rules
            if "category" not in result:
                merchant = result.get("merchant_name", "").lower()
                subject_keywords = email_body.lower()
                found_category = None
                for category, senders in email_map.items():
                    for sender in senders:
                        if sender.lower() in subject_keywords:
                            found_category = category
                            break
                    if found_category:
                        break
                if not found_category:
                    for keyword, cat in category_map.items():
                        if keyword.lower() in merchant:
                            found_category = cat
                            break
                result["category"] = found_category if found_category else "others"
            return result
    return None

def verify_html_cleanup(cleaned_text):
    """Check if HTML tags or major HTML constructs still remain in the cleaned text."""
    if (
        re.search(r'<[^>]+>', cleaned_text)
        or "<html" in cleaned_text.lower()
        or "<!doctype" in cleaned_text.lower()
    ):
        print("WARNING: HTML cleanup incomplete - tags still present.")