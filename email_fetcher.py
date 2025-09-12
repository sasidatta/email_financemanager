import imaplib
import os
from dotenv import load_dotenv
from config_loader import Config
import pdb
import sys
# Load .env if present
load_dotenv()

config = Config()
email_conf = config.email

def get_config_value(key, default=None):
    return os.environ.get(key, default)

EMAIL = get_config_value('YAHOO_EMAIL', email_conf.get('address'))
PASSWORD = get_config_value('YAHOO_APP_PASSWORD', email_conf.get('password'))
IMAP_SERVER = get_config_value('IMAP_SERVER', email_conf.get('imap_server'))

def connect_to_imap(server=None):
    server = server or IMAP_SERVER
    imap = imaplib.IMAP4_SSL(server)
    imap.login(EMAIL, PASSWORD)
    imap.select("INBOX")
    return imap 

# Helper to fetch by a list of message ids in batches
_DEF_BATCH = 50

def _fetch_by_ids(imap, ids):
    emails = []
    if not ids:
        return emails
    for i in range(0, len(ids), _DEF_BATCH):
        batch = ids[i:i + _DEF_BATCH]
        ids_str = b",".join(batch)
        status, msg_data = imap.fetch(ids_str, "(RFC822)")
        if status == "OK" and msg_data:
            for part in msg_data:
                if isinstance(part, tuple):
                    emails.append(part[1])
    return emails

# Build an IMAP SEARCH query for a single keyword with date constraints
_DEF_FIELDS = ["SUBJECT", "BODY"]

def _search_ids_for_keyword(imap, keyword, since=None, before=None, search_fields=None):
    terms = []
    if since:
        terms += ["SINCE", since]
    if before:
        terms += ["BEFORE", before]
    fields = search_fields or _DEF_FIELDS
    # For field in SUBJECT/BODY, build OR chain: OR SUBJECT "kw" BODY "kw"
    field_terms = []
    for field in fields:
        field_terms += [field, f'"{keyword}"']
    # Wrap with ORs if multiple fields
    query_parts = terms[:]
    if len(fields) == 1:
        query_parts += field_terms
    else:
        # OR chaining: OR A B, then OR (OR A B) C ...
        from collections import deque
        ft = deque(field_terms)
        # initialize with first pair (FIELD "kw")
        current = [ft.popleft(), ft.popleft()]
        while ft:
            next_pair = [ft.popleft(), ft.popleft()]
            current = ["OR"] + current + next_pair
        query_parts += current
    status, data = imap.search(None, *query_parts)
    if status != "OK" or not data or not data[0]:
        return []
    return data[0].split()

# Fetch emails from the last n_days (default: 3) with optional keyword filtering
from datetime import datetime, timedelta

def fetch_emails_last_n_days(imap, n_days=3, keywords=None, search_fields=None):
    date_since = (datetime.now() - timedelta(days=n_days)).strftime("%d-%b-%Y")
    if keywords:
        all_ids = set()
        for kw in keywords:
            ids = _search_ids_for_keyword(imap, kw, since=date_since, before=None, search_fields=search_fields)
            for _id in ids:
                all_ids.add(_id)
        ordered_ids = sorted(all_ids, key=lambda x: int(x))
        return _fetch_by_ids(imap, ordered_ids)
    # Fallback: no keywords, fetch all since date
    status, data = imap.search(None, f'(SINCE "{date_since}")')
    if status != "OK":
        return []
    email_ids = data[0].split()
    return _fetch_by_ids(imap, email_ids)

def fetch_emails_date_range(imap, start_date, end_date, keywords=None, search_fields=None):
    since_str = start_date.strftime("%d-%b-%Y")
    before_str = (end_date + timedelta(days=1)).strftime("%d-%b-%Y")
    if keywords:
        all_ids = set()
        for kw in keywords:
            ids = _search_ids_for_keyword(imap, kw, since=since_str, before=before_str, search_fields=search_fields)
            for _id in ids:
                all_ids.add(_id)
        ordered_ids = sorted(all_ids, key=lambda x: int(x))
        return _fetch_by_ids(imap, ordered_ids)
    status, data = imap.search(None, f'(SINCE "{since_str}" BEFORE "{before_str}")')
    if status != "OK":
        return []
    email_ids = data[0].split()
    return _fetch_by_ids(imap, email_ids)

def fetch_emails(imap, n_days=None, start_date=None, end_date=None, keywords=None, search_fields=None):
    if n_days is not None:
        return fetch_emails_last_n_days(imap, n_days, keywords=keywords, search_fields=search_fields)
    elif start_date is not None and end_date is not None:
        return fetch_emails_date_range(imap, start_date, end_date, keywords=keywords, search_fields=search_fields)
    else:
        raise ValueError("Provide either n_days or start_date & end_date")