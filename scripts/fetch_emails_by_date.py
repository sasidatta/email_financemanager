# Add BeautifulSoup import for HTML cleanup
import os
import imaplib
from email.parser import BytesParser
from email import policy
from email import message_from_bytes
from email.policy import default
from dotenv import load_dotenv
from datetime import datetime
import pdb
import sys
from bs4 import BeautifulSoup
# Load environment variables
load_dotenv()

EMAIL = os.getenv("YAHOO_EMAIL")
PASSWORD = os.getenv("YAHOO_APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.mail.yahoo.com")


# Function to clean up HTML content using BeautifulSoup
def cleanup_html_content(html: str) -> str:
    """
    Cleans up HTML email content and returns plain text.
    """
    soup = BeautifulSoup(html, "html.parser")
    # You can customize this to extract only the text or do more advanced cleaning
    return soup.get_text(separator="\n", strip=True)

def decode_email_body(raw_email_bytes):
    msg = message_from_bytes(raw_email_bytes, policy=default)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode(errors="ignore")
                body = cleanup_html_content(html_body)
                break
        if not body:
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
        body = cleanup_html_content(body)
    return body

def fetch_emails_by_date(date_str, output_file="emails_dump.txt"):
    """
    Fetch emails from IMAP server for a specific date.
    date_str: YYYY-MM-DD
    """
    try:
        # Convert to IMAP search format (DD-Mon-YYYY)
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        search_date = date_obj.strftime("%d-%b-%Y")

        # Connect to IMAP
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(EMAIL, PASSWORD)
        imap.select("inbox")

        # Search for emails on the given date
        status, data = imap.search(None, f'ON "{search_date}"')
        if status != "OK":
            print(f"No messages found on {date_str}")
            return

        #pdb.Pdb(stdout=sys.stdout).set_trace()

        email_ids = data[0].split()
        print(f"Found {len(email_ids)} emails on {date_str}")

        with open(output_file, "w", encoding="utf-8") as f:
            for eid in email_ids:
                status, msg_data = imap.fetch(eid, "(BODY.PEEK[])")
                if status != "OK":
                    continue

                raw_bytes = msg_data[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
                #pdb.Pdb(stdout=sys.stdout).set_trace()

                subject = msg.get("Subject", "")
                body = decode_email_body(raw_bytes)

                f.write("="*80 + "\n")
                f.write(f"Date: {date_str}\n")
                f.write(f"Subject: {subject}\n\n")
                f.write(body + "\n\n")

        imap.logout()
        print(f"Emails written to {output_file}")

    except Exception as e:
        print(f"Error fetching emails: {e}")

if __name__ == "__main__":
    user_date = input("Enter date (YYYY-MM-DD): ").strip()
    fetch_emails_by_date(user_date)