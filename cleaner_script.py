from pathlib import Path
import re
import sys
import pdb
from bs4 import BeautifulSoup

def cleanup_html_content(html: str) -> str:
    """Clean up HTML content, removing tags and unnecessary whitespace."""
    # Basic HTML tag removal
    cleaned = re.sub(r'<[^>]+>', '', html)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def verify_html_cleanup(cleaned_text: str):
    """Check if HTML tags or major HTML constructs still remain in the cleaned text."""
    if (
        re.search(r'<[^>]+>', cleaned_text)
        or "<html" in cleaned_text.lower()
        or "<!doctype" in cleaned_text.lower()
    ):
        print("WARNING: HTML cleanup incomplete - tags found.")
    else:
        print("INFO: HTML cleanup successful - no tags found.")

