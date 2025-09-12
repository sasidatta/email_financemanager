"""
Regex patterns for extracting transaction data from various bank email formats.
"""

import re

bank_regex_patterns = {
    # SBI Cashback Credit Card
    "SBI_CASHBACK_CREDIT_CARD": {
        "pattern": re.compile(
            r"(?i)(Rs|₹|INR)\.?\s*([\d,]+\.\d{2})\s+spent on your SBI Credit Card ending\s+(\d{4})\s+at\s+(.+?)\b",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "card_number",
            "merchant_name"
        ],
        "card": "SBI Credit Card",
        "transactiontype": "Credit Card Debit"
    },
    
    # SBI Credit Card Transaction (standard format)
    "SBI_CREDIT_CARD": {
        "pattern": re.compile(
            r"(?i)Rs\.?([\d,]+\.\d{2})\s+spent on your SBI Credit Card ending\s+(\d{4})\s+at\s+(.+?)\b",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "card_number",
            "merchant_name"
        ],
        "card": "SBI Credit Card",
        "transactiontype": "Credit Card Debit"
    },
    
    # SBI UPI Transaction
    "SBI_UPI": {
        "pattern": re.compile(
            r"(?i)(Rs|₹|INR)\.?\s*([\d,]+\.\d{2})\s+has been debited from your SBI account\s+(XX\d{4})\s+via UPI.*?to\s+([\w@.]+)\s+(.+?)\s+UPI Reference No:\s+(\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "account_number",
            "merchant_paymentid",
            "merchant_name",
            "transactionid"
        ],
        "transactiontype": "UPI Debit"
    },
    # HDFC UPI Credit Card
    "HDFC_CC_UPI": {
        "pattern": re.compile(
            r"(?i)(Rs|₹|INR)\.?\s*([\d,]+\.\d{2})\s+has been debited from your HDFC Bank RuPay Credit Card\s+(XX\d{4})\s+to\s+([\w@.]+)\s+(.*?)\.\s*Your UPI transaction reference number is\s+(\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "card_number",
            "merchant_paymentid",
            "merchant_name",
            "transactionid"
        ],
        "card": "HDFC Bank RuPay Credit Card",
        "transactiontype": "UPI Debit"
    },
    "HDFC Credit card": {
        "pattern": re.compile(
            r"(?i)Rs\.?\s*([\d,]+\.\d{2}).*?HDFC Bank RuPay Credit Card\s+(XX\d{4}).*?to\s+([\w@.]+)\s+(.*?)\s+UPI transaction reference number is\s+(\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "card_number",
            "merchant_paymentid",
            "merchant_name",
            "transactionid"
        ],
        "card": "HDFC Bank RuPay Credit Card",
        "transactiontype": "Credit Card Debit"
    },
    # ICICI Credit Card (matches date with or without time, flexible merchant info)
    "APAY ICICI Credit Card": {
        "pattern": re.compile(
            r"ICICI Bank Credit Card\s+(XX\d{4}).*?transaction of\s+(INR|Rs\.?|₹)\s*([\d,]+\.\d{2}).*?Info:\s*([^.\n]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "card_number",
            "currency",
            "amount",
            "merchant_name"
        ],
        "transactionid": "",
        "merchant_paymentid": "",
        "card": "ICICI Bank Credit Card",
        "transactiontype": "Credit Card Debit"
    },
    # Kotak IMPS Debit (accepts both 09-May-2025 and 09-05-2025)
    "KOTAK_IMPS_DEBIT": {
        "pattern": re.compile(
            r"account\s+xx\d+\s+is debited for (INR|Rs\.?|₹)\s*([\d,]+\.\d{2}).*?Beneficiary Name:\s+(.*?)\s+Beneficiary Account No:\s+(.*?)\s+Beneficiary IFSC:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks: ?(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
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
            r"account\s+xx\d+\s+is credited by (INR|Rs\.?|₹)\s*([\d,]+\.\d{2}).*?Sender Name:\s+(.*?)\s+Sender Mobile No:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks ?:(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
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
            r"A/c no\. (XX\d+).*?debited with (INR|Rs\.?|₹) ([\d,]+\.\d{2}) by ([\w\d_\-]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "currency",
            "amount",
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
            r"Amount Debited:\s+(INR|Rs|₹)\s*([\d,]+\.\d{2})\s+Account Number:\s+(XX\d{4})\s+Transaction Info:\s+(UPI/[^/]+/\d+/[^.\n]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "account_number",
            "transaction_info"
        ],
        "card": "AXIS Bank UPI",
        "transactiontype": "UPI Debit"
    },
    # AXIS Bank Credit Card
    "AXIS_CREDIT_CARD": {
        "pattern": re.compile(
            r"Transaction Amount:\s*(INR|Rs|₹)\s*([\d,\.]+)\s*"
            r"Merchant Name:\s*([^\n]+)\s*"
            r"Axis Bank Credit Card No\.\s*(XX\d+)\s*"
            r"Date & Time:\s*([^\n]+)\s*"
            r"Available Limit\*:\s*(INR|Rs|₹)\s*([\d,\.]+)\s*"
            r"Total Credit Limit\*:\s*(INR|Rs|₹)\s*([\d,\.]+)",
            re.IGNORECASE
        ),
        "fields": [
            "currency",
            "amount",
            "merchant_name",
            "card_number",
            "datetime",
            "currency_limit",
            "available_limit",
            "currency_total",
            "total_limit"
        ],
        "card": "Axis Bank Credit Card",
        "transactiontype": "Credit Card Debit"
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
            r"(?:₹|INR)\s*([\d,]+\.\d{2})Paid Successfully.*?Payment Id\s*(pay_\w+).*?Method\s*card\s+.*?(\d{4}).*?Email\s*(.*?)\s+Mobile Number\s*(\+\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "payment_id",
            "card_last4",
            "email",
            "mobile"
        ],
        "transactiontype": "Card Payment"
    },
    "RAZORPAY_MERCHANT_PAYMENT": {
        "pattern": re.compile(
            r"(?:₹|INR)\s*([\d,]+\.\d{2})Paid Successfully.*?Payment Id\s*(pay_\w+).*?Method\s*card\s+.*?(\d{4}).*?Email\s*(.*?)\s+Mobile Number\s*(\+\d+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "payment_id",
            "card_last4",
            "email",
            "mobile"
        ],
        "transactiontype": "Card Payment"
    },
    # RBL Bank Credit Card
    "RBL_CREDIT_CARD": {
        "pattern": re.compile(
            r"(INR|Rs|₹)\.?\s*([\d,]+\.\d{2})\s+spent at\s+(.+?)\s+.*?RBL Bank credit card\s+\((\d{4})\)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "currency",
            "amount",
            "merchant_name",
            "card_number"
        ],
        "card": "RBL Bank Credit Card",
        "transactiontype": "Credit Card Debit"
    },
    # Generic UPI txn fallback
    "GENERIC_UPI_TXN": {
        "pattern": re.compile(r"UPI txn", re.IGNORECASE),
        "fields": [],
        "transactiontype": "UPI",
        "category": "UPI"
    }
}

# Billing regex patterns for extracting utility bill payment transactions
billing_regex_patterns = {
    "POWER_BILL_PAYMENT": {
        "pattern": re.compile(
            r"bill payment of Electricity.*?Paid to\s+(.+?)\s+.*?Amount\s+₹?([\d,]+\.?\d*)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": ["merchant_name", "amount"],
        "transactiontype": "bill_payment",
        "category": "utilities"
    }
}

def select_best_pattern(email_body):
    """Return the best matching pattern and match object for a given email body."""
    for name, data in bank_regex_patterns.items():
        match = data["pattern"].search(email_body)
        if match:
            return name, match
    return None, None


# Helper function for billing patterns
def select_best_billing_pattern(email_body):
    """Return the best matching billing pattern and match object for a given email body."""
    for name, data in billing_regex_patterns.items():
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
    # Ensure merchant_name is never empty
    normalized["merchant_name"] = normalized.get("merchant_name") or "unknown"
    return normalized