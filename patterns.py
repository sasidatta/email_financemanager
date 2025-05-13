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
    # ICICI Credit Card
    "ICICI": {
        "pattern": re.compile(
            r"ICICI Bank Credit Card\s+(XX\d{4}).*?transaction of INR\s+([\d,]+\.\d{2}).*?on\s+([A-Za-z]+\s+\d{02},\s+\d{4}).*?Info:\s+(.*?)\.",
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
    # Kotak IMPS Debit
    "KOTAK_IMPS_DEBIT": {
        "pattern": re.compile(
            r"your account\s+xx\d+\s+is debited for Rs\.?\s*([\d,]+\.\d{2}) on (\d{2}-[A-Za-z]{3}-\d{4}).*?Beneficiary Name:\s+(.*?)\s+Beneficiary Account No:\s+(.*?)\s+Beneficiary IFSC:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks:\s+(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
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
            r"your account\s+xx\d+\s+is credited by Rs\.?\s*([\d,]+\.\d{2}) on (\d{2}-[A-Za-z]{3}-\d{4}).*?Sender Name:\s+(.*?)\s+Sender Mobile No:\s+(.*?)\s+IMPS Reference No:\s+(\d+).*?Remarks\s+:\s+(.*?) ",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "amount",
            "date",
            "sender_name",
            "sender_mobile",
            "transactionid",
            "remarks"
        ],
        "transactiontype": "IMPS Credit"
    },
    # Axis Bank Debit
    "AXIS_DEBIT": {
        "pattern": re.compile(
            r"A/c no\. (XX\d+).*?debited with INR ([\d,]+\.\d{2}) on (\d{2}-\d{2}-\d{4}) (\d{2}:\d{2}:\d{2}) IST by (.*?)\.",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "amount",
            "date",
            "time",
            "reference"
        ],
        "transactiontype": "Debit"
    },
    # Axis NEFT
    "AXIS_NEFT": {
        "pattern": re.compile(
            r"NEFT for your A/c no\. (XX\d+) for an amount of INR ([\d,]+\.\d{2}) has been initiated with transaction reference no\. (\w+)\.",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "amount",
            "transactionid"
        ],
        "transactiontype": "NEFT"
    },
    # AXIS Bank UPI Debit
    "AXIS_UPI_DEBIT": {
        "pattern": re.compile(
            r"(INR)\s*([\d,]+\.\d{2})\s+Account Number:\s+(XX\d{4})\s+Date & Time:\s+(\d{2}-\d{2}-\d{2}),\s+(\d{2}:\d{2}:\d{2})\s+Transaction Info:\s+(UPI/P2A/\d+/.+?)\s+If this transaction was not initiated by you:",
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
    # Generic fallback for INR/Rs. transactions
    "GENERIC": {
        "pattern": re.compile(
            r"(?:INR|Rs\\.?)\\s*([\d,]+\\.\d{2})", re.IGNORECASE),
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
    "AXIS_EMI_DEBIT": {
        "pattern": re.compile(
            r"A/c no\. (XX\d+).*?debited with INR ([\d,]+\.\d{2}) on (\d{2}-\d{2}-\d{4}) (\d{2}:\d{2}:\d{2}) IST by ([\w\d_]+)",
            re.IGNORECASE | re.DOTALL
        ),
        "fields": [
            "account_number",
            "amount",
            "date",
            "time",
            "reference"
        ],
        "transactiontype": "EMI Debit"
    },
    # RBL Bank Credit Card
    "RBL_CREDIT_CARD": {
        "pattern": re.compile(
            r"(INR)\s*([\d,]+\.\d{2})\s+spent at\s+(.*?)\s+on\s+(\d{2}-\d{2}-\d{4})\s+.*?RBL Bank credit card\s+\((\d{4})\)",
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

def normalize_debit_transaction(data):
    # Map all possible fields to your canonical schema
    normalized = {
        "email_address": data.get("email_address", ""),
        "transactionid": data.get("transactionid", ""),
        "amount": data.get("amount", 0.0),
        "merchant_name": (
            data.get("merchant_name") or
            data.get("beneficiary_name") or
            data.get("reference") or
            data.get("remarks") or
            ""
        ),
        "transactiontype": data.get("transactiontype", ""),
        "category": data.get("category", ""),
        "date": data.get("date", None),
        "card_number": data.get("card_number", ""),
        "merchant_paymentid": data.get("merchant_paymentid", ""),
        "currency": data.get("currency", "INR"),
    }
    return normalized