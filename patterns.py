"""
Regex patterns for extracting transaction data from various bank email formats.
"""

import re

bank_regex_patterns = {
    # SBI Cashback Credit Card
    "SBI_CASHBACK_CREDIT_CARD": {
        "pattern": re.compile(
            r"(?i)(Rs|₹|INR)\.?\s*([\d,]+\.\d{2})\s+spent on your SBI Credit Card ending\s+(\d{4})\s+at\s+(.*?)\s+on\s+(\d{2}/\d{2}/\d{2})",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "card_number",
            "merchant_name",
            "date"
        ],
        "card": "SBI Credit Card",
        "transactiontype": "Credit card"
    },
    # HDFC UPI Credit Card
    "HDFC_CC_UPI": {
        "pattern": re.compile(
            r"(?i)(Rs|₹|INR)\.?\s*([\d,]+\.\d{2}) has been debited from your HDFC Bank RuPay Credit Card\s+(XX\d{4}) to\s+([\w@.]+)\s+(.*?)\s+on\s+(\d{2}-\d{2}-\d{2})\. Your UPI transaction reference number is\s+(\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
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
    "HDFC Credit card": {
        "pattern": re.compile(
            r"Rs\\.?([\d,]+\\.\d{2}).*?HDFC Bank RuPay Credit Card\\s+(XX\\d{4}).*?to\\s+([\w@.]+)\\s+(.*?)\\s+on\\s+(\\d{2}-\\d{2}-\\d{2}).*?UPI transaction reference number is\\s+(\\d+)",
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
        "transactiontype": "Credit card"
    },
    # ICICI Credit Card (matches date with or without time, flexible merchant info)
    "ICICI": {
        "pattern": re.compile(
            r"ICICI Bank Credit Card\s+(XX\d{4}).*?transaction of (INR|Rs\.?|₹)\s*([\d,]+\.\d{2}).*?on\s+([A-Za-z]+\s+\d{2},\s+\d{4})(?: at ([\d:]+))?.*?Info:\s*([^.\n]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "card_number",
            "currency",
            "amount",
            "date",
            "time",
            "merchant_name"
        ],
        "transactionid": "",
        "merchant_paymentid": "",
        "card": "ICICI Bank Credit Card",
        "transactiontype": "Credit card"
    },
    # Kotak IMPS Debit (accepts both 09-May-2025 and 09-05-2025)
    "KOTAK_IMPS_DEBIT": {
        "pattern": re.compile(
            r"account\s+xx\d+\s+is debited for (INR|Rs\.?|₹)\s*([\d,]+\.\d{2}) on (\d{2}-[A-Za-z]{3}-\d{4}|\d{2}-\d{2}-\d{4}).*?Beneficiary Name:\s+(.*?)\s+Beneficiary Account No:\s+(.*?)\s+Beneficiary IFSC:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks: ?(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "date",
            "beneficiary_name",
            "beneficiary_account",
            "beneficiary_ifsc",
            "transactionid",
            "remarks"
        ],
        "transactiontype": "IMPS Debit"
    },
    # Kotak IMPS Credit
    "KOTAK_IMPS_CREDIT": {
        "pattern": re.compile(
            r"account\s+xx\d+\s+is credited by (INR|Rs\.?|₹)\s*([\d,]+\.\d{2}) on (\d{2}-[A-Za-z]{3}-\d{4}|\d{2}-\d{2}-\d{4}).*?Sender Name:\s+(.*?)\s+Sender Mobile No:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks ?:(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "date",
            "sender_name",
            "sender_mobile",
            "transactionid",
            "remarks"
        ],
        "transactiontype": "IMPS Credit"
    },
    # Axis Bank EMI Debit
    "AXIS_EMI_DEBIT": {
        "pattern": re.compile(
            r"A/c no\. (XX\d+).*?debited with (INR|Rs\.?|₹) ([\d,]+\.\d{2}) on (\d{2}-\d{2}-\d{4}) (\d{2}:\d{2}:\d{2}) IST by ([\w\d_\-]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "currency",
            "amount",
            "date",
            "time",
            "reference"
        ],
        "transactiontype": "EMI Debit"
    },
    # Axis NEFT
    "AXIS_NEFT": {
        "pattern": re.compile(
            r"NEFT for your A/c no\. (XX\d+) for an amount of (INR|Rs\.?|₹) ([\d,]+\.\d{2}) has been initiated with transaction reference no\. (\w+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "currency",
            "amount",
            "transactionid"
        ],
        "transactiontype": "NEFT"
    },
    # AXIS Bank UPI Debit
    "AXIS_UPI_DEBIT": {
        "pattern": re.compile(
            r"Amount Debited:\s+(INR|Rs|₹)\s*([\d,]+\.\d{2})\s+Account Number:\s+(XX\d{4})\s+Date & Time:\s+(\d{2}-\d{2}-\d{2}),\s+(\d{2}:\d{2}:\d{2})\s+IST\s+Transaction Info:\s+(UPI/P2A/\d+/.+?)\s+If this transaction was not initiated by you:",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "account_number",
            "date",
            "time",
            "transaction_info"
        ],
        "card": "AXIS Bank UPI",
        "transactiontype": "UPI Debit"
    },
    # Generic fallback for INR/Rs/₹ transactions
    "GENERIC": {
        "pattern": re.compile(
            r"(?:INR|Rs\\.?|₹)\\s*([\d,]+\\.\d{2})", re.IGNORECASE),
        "fields": ["amount"],
        "transactiontype": "Unknown"
    },
    # Razorpay Card Payment
    "RAZORPAY_CARD_PAYMENT": {
        "pattern": re.compile(
            r"(?:₹|INR)\s*([\d,]+\.\d{2})Paid Successfully.*?Payment Id\s*(pay_\w+).*?Method\s*card\s+.*?(\d{4}).*?Paid On\s*([\d\s:AMP]+).*?Email\s*(.*?)\s+Mobile Number\s*(\+\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "payment_id",
            "card_last4",
            "paid_on",
            "email",
            "mobile"
        ],
        "transactiontype": "Card Payment"
    },
    "RAZORPAY_MERCHANT_PAYMENT": {
        "pattern": re.compile(
            r"(?:₹|INR)\s*([\d,]+\.\d{2})Paid Successfully.*?Payment Id\s*(pay_\w+).*?Method\s*card\s+.*?(\d{4}).*?Paid On\s*([\d\s:AMP]+).*?Email\s*(.*?)\s+Mobile Number\s*(\+\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "payment_id",
            "card_last4",
            "paid_on",
            "email",
            "mobile"
        ],
        "transactiontype": "Card Payment"
    },
    # RBL Bank Credit Card
    "RBL_CREDIT_CARD": {
        "pattern": re.compile(
            r"(INR|Rs|₹)\.?\s*([\d,]+\.\d{2})\s+spent at\s+(.*?)\s+on\s+(\d{2}-\d{2}-\d{4})\s+.*?RBL Bank credit card\s+\((\d{4})\)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "merchant_name",
            "date",
            "card_number"
        ],
        "card": "RBL Bank Credit Card",
        "transactiontype": "Credit card"
    }
}

def select_best_pattern(email_body):
    """Return the best matching pattern and match object for a given email body."""
    for name, data in bank_regex_patterns.items():
        match = data["pattern"].search(email_body)
        if match:
            return name, match
    return None, None

REQUIRED_FIELDS = [
    "email_address",
    "transactionid",
    "amount",
    "merchant_name",
    "transactiontype",   # 'credit' or 'debit', also used as direction
    "payment_type",      # e.g., 'HDFC Bank RuPay Credit Card', 'IMPS', 'NEFT'
    "category",
    "date",
    "account_number",
    "merchant_paymentid",
    "currency",
    "remarks"
]

def normalize_transaction(data):
    """Ensure all required fields are present and normalized."""
    normalized = {}
    for field in REQUIRED_FIELDS:
        normalized[field] = data.get(field, "")
    # Normalize transactiontype (direction)
    ttype = normalized["transactiontype"].lower()
    if "credit" in ttype:
        normalized["transactiontype"] = "credit"
    elif "debit" in ttype:
        normalized["transactiontype"] = "debit"
    else:
        # Fallback: use keywords in payment_type/merchant_name/remarks
        pt = normalized["payment_type"].lower()
        if "credit" in pt:
            normalized["transactiontype"] = "credit"
        elif "debit" in pt:
            normalized["transactiontype"] = "debit"
        else:
            normalized["transactiontype"] = ""
    return normalized