"""
Mapping of transaction keywords and sender emails to categories for automatic email-based finance classification.
"""

category_map = {
    "food": ["swiggy", "zomato", "restaurant"],
    "fuel": ["indian oil", "hpcl", "fuel", "petrol", "diesel"],
    "shopping": ["amazon", "flipkart", "myntra"],
    "utilities": ["electricity", "water", "utility bill", "mobile recharge", "amazon pay", "broadband", "act fibernet", "act", "jio", "jio mobile", "internet bill", "broadband bill"],
    "travel": ["ola", "uber", "irctc", "goibibo", "makemytrip"],
    "investments": ["smallcase", "investment", "sip", "mutual fund"],
    "payment_failed": ["payment failed", "transaction failed", "refund", "reversed"],
    "dmat": [
        "demat account", "equity contract note", "funds / securities balance",
        "securities balance", "outcome of board meeting", "change in base ter", "e-voting"
    ],
    "dividend": ["dividend"],
    "promotions": ["emi", "gift", "add-on", "promotion", "deal", "invite", "offer"],
    "login": ["oauth application", "login notification", "login alert", "otp", "one time password"],
    "upi": ["upi txn", "you have done a upi txn", "upi payment", "bhim upi", "gpay", "phonepe"],
    "otp": ["transaction otp", "otp for transaction"]
}

email_map = {
    "hdfc": ["alerts@hdfcbank.net"],
    "icici": ["credit_cards@icicibank.com"],
    "rbl": ["RBLAlerts@rblbank.com"],
    "amazon": ["no-reply@amazonpay.in"],
    "dmat": [
        "donotreply.evoting@cdslindia.co.in",
        "nse_alerts@nse.co.in",
        "services@cdslindia.co.in",
        "donotreply@camsonline.com",
        "no-reply-contract-notes@reportsmailer.zerodha.net"
    ]
}

