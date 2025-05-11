from pathlib import Path
import re
import sys
import pdb
from bs4 import BeautifulSoup

def cleanup_html_content(html_body):
    """Clean HTML content by stripping tags and normalizing whitespace."""
    body = None
    if not body and html_body:
        # Strip HTML tags using BeautifulSoup
        soup = BeautifulSoup(html_body, "html.parser")
        # Remove all script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        body = soup.get_text(separator=' ')
        body = re.sub(r'<[^>]+>', '', body)  # Extra cleanup, though BeautifulSoup usually handles it
        body = re.sub(r'\s+', ' ', body).strip()  # Normalize whitespace
        #verify_html_cleanup(body)
    return body

def verify_html_cleanup(cleaned_text):
    """Check if HTML tags or major HTML constructs still remain in the cleaned text."""
    if (
        re.search(r'<[^>]+>', cleaned_text)
        or "<html" in cleaned_text.lower()
        or "<!doctype" in cleaned_text.lower()
    ):
        pass
    else:
        print("INFO: HTML cleanup successful - no tags found.")

