import os
import sys
import imaplib
from email import message_from_bytes
from email.policy import default
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

# Load .env
load_dotenv()

EMAIL = os.environ.get("YAHOO_EMAIL")
PASSWORD = os.environ.get("YAHOO_APP_PASSWORD")
IMAP_SERVER = os.environ.get("IMAP_SERVER")

# Connect to IMAP
imap = imaplib.IMAP4_SSL(IMAP_SERVER)
imap.login(EMAIL, PASSWORD)
imap.select("INBOX")

# Date range: last 2 days
ist = pytz.timezone("Asia/Kolkata")
since_date = (datetime.now(ist) - timedelta(days=2)).strftime("%d-%b-%Y")

# Search for ICICI emails
subject_filter = "Transaction alert for your ICICI Bank Credit Card"
status, data = imap.search(None, f'(SINCE "{since_date}" SUBJECT "{subject_filter}")')

if status != "OK":
    print("No emails found.")
    sys.exit(0)

email_ids = data[0].split()
print(f"Found {len(email_ids)} emails in last 2 days.")

for eid in email_ids:
    status, msg_data = imap.fetch(eid, "(RFC822)")
    if status != "OK":
        continue

    for part in msg_data:
        if isinstance(part, tuple):
            msg = message_from_bytes(part[1], policy=default)
            subject = msg.get("Subject")
            raw_date = msg.get("Date")

            # Try Date header first
            email_timestamp = None
            if raw_date:
                try:
                    dt = parsedate_to_datetime(raw_date)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=pytz.UTC)
                    email_timestamp = dt.astimezone(ist)
                except Exception as e:
                    print(f"Failed to parse Date header: {raw_date} - {e}", file=sys.stderr)

            # Fallback: use first Received header if Date is missing
            if email_timestamp is None:
                received_headers = msg.get_all("Received", [])
                if received_headers:
                    try:
                        # Usually Received: headers start with "from ...; <date>"
                        last_part = received_headers[-1].rsplit(";", 1)[-1].strip()
                        dt = parsedate_to_datetime(last_part)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=pytz.UTC)
                        email_timestamp = dt.astimezone(ist)
                        print("Using Received header fallback for timestamp.")
                    except Exception as e:
                        print(f"Failed to parse Received header date: {last_part} - {e}", file=sys.stderr)

            print("\nSubject:", subject)
            print("Raw Date header:", raw_date)
            print("Parsed email timestamp (IST):", email_timestamp)

imap.logout()