import base64
import re
from email import message_from_bytes
from email.policy import default
import sys
from bs4 import BeautifulSoup
import pdb
from categories import category_map
from categories import email_map
bank_regex_patterns = {
    "HDFC": {
        "pattern": re.compile(
            r"Rs\.?([\d,]+\.\d{2}).*?Credit Card\s+(XX\d{4}).*?to\s+([A-Z0-9@\.]+)\s+(.*?)\s+on\s+(\d{2}-\d{2}-\d{2}).*?UPI transaction reference number is\s+(\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "card_number",
            "merchant_paymentid",
            "merchant_name",
            "date",
            "transactionid"
        ],
        "card": "HDFC Bank RuPay Credit Card",
        "transactiontype": "Credit card UPI"
    },
    "ICICI": {
        "pattern": re.compile(
            r"ICICI Bank Credit Card\s+(XX\d{4}).*?transaction of INR\s+([\d,]+\.\d{2}).*?on\s+([A-Za-z]+\s+\d{2},\s+\d{4}).*?Info:\s+(.*?)\.",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "card_number",
            "amount",
            "date",
            "merchant_name"
        ],
        "transactionid": "",
        "merchant_paymentid": "",
        "card": "ICICI Bank Credit Card",
        "transactiontype": "Credit card"
    },

}

def decode_email_body(raw_email_bytes):
    # Ensure input is bytes
    if isinstance(raw_email_bytes, str):
        raw_email_bytes = raw_email_bytes.encode('utf-8', errors='replace')

    # Parse email using the standard library
    #pdb.Pdb(stdout=sys.__stdout__).set_trace()
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
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        body = payload.decode(charset, errors="replace")


    #pdb.Pdb(stdout=sys.__stdout__).set_trace()


    if not body and html_body:
        # Strip HTML tags using BeautifulSoup
        soup = BeautifulSoup(html_body, "html.parser")
        body = soup.get_text()
        verify_html_cleanup(body)

    return body or ""

def clean_email_body(body):
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    cleaned_body = body.strip()  # Removes leading and trailing spaces/newlines
    cleaned_body = re.sub(r'\s+', ' ', cleaned_body)  # Replace multiple spaces or newlines with a single space
    return cleaned_body

def extract_transaction_data(email_body):
    #pdb.Pdb(stdout=sys.__stdout__).set_trace()
    email_body = decode_email_body(email_body) 
    email_body = clean_email_body(email_body)
    with open("dump.txt", "a", encoding="utf-8") as dump_file:
        dump_file.write(email_body + "\n" + "="*80 + "\n")

    #pdb.Pdb(stdout=sys.__stdout__).set_trace()

    for bank_name, data in bank_regex_patterns.items():
        if bank_name.lower() in email_body.lower():
            match = data["pattern"].search(email_body)
            if match:
                values = match.groups()
                amount_text = values[data["fields"].index("amount")]
                currency = "INR" if "INR" in email_body or "Rs" in amount_text else "UNKNOWN"

                result = {
                    "currency": currency,
                    "card": data["card"]
                }
                result.update(dict(zip(data["fields"], values)))
                import logging
                logging.basicConfig(level=logging.INFO)
                for key, value in result.items():
                    logging.info(f"{key}: {value}")
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
                    # Set category based on merchant_name or other rules
                    merchant = result.get("merchant_name", "").lower()
                    subject_keywords = email_body.lower()

                    found_category = None

                    # First try email_map based on subject content
                    for category, senders in email_map.items():
                        for sender in senders:
                            if sender.lower() in subject_keywords:
                                found_category = category
                                break
                        if found_category:
                            break

                    # If not found, try category_map using merchant name
                    if not found_category:
                        for keyword, cat in category_map.items():
                            if keyword.lower() in merchant:
                                found_category = cat
                                break

                    result["category"] = found_category if found_category else "others"

                #pdb.Pdb(stdout=sys.__stdout__).set_trace()
                return result

    return None

def verify_html_cleanup(cleaned_text):
    """Check if HTML tags still remain in the cleaned text."""
    if re.search(r'<[^>]+>', cleaned_text):
        print("WARNING: HTML cleanup incomplete - tags still present.")
    else:
        print("INFO: HTML cleanup successful - no tags found.")