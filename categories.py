"""
Category and email mapping for transaction classification.
"""

category_map = {
    "food": ["swiggy", "zomato", "restaurant"],
    "fuel": ["indian oil", "hpcl", "fuel"],
    "shopping": ["amazon", "flipkart", "myntra"],
    "utilities": ["electricity", "water", "bill", "amazon pay","Mobile recharge"],
    "travel": ["ola", "uber", "irctc", "goibibo"],
    "investments": ["smallcase", "investment"],
    "payment_failed": ["payment failed", "transaction failed", "refund"],
    "dmat": ["Demat Account", "Equity Contract Note", "Funds / Securities Balance", "Securities Balance", "Outcome of Board Meeting","Change in BASE TER","e-voting for"],
    "dividend": ["dividend"],
    "promotions": ["emi", "gift", "add-on", "promotions","deals","deal","Invite"],
    "login": ["oauth application", "login notification", "login alerts","One Time Password","One Time Password","OTP"],
    "UPI": ["upi txn", "you have done a upi txn"],
    "OTP": ["Transaction OTP"]
}

email_map = {
    "hdfc": ["alerts@hdfcbank.net"],
    "icici": ["credit_cards@icicibank.com"],
    "rbl": ["RBLAlerts@rblbank.com"],
    "amazon": ["no-reply@amazonpay.in"],
    "dmat": ["donotreply.evoting@cdslindia.co.in","nse_alerts@nse.co.in","services@cdslindia.co.in","donotreply@camsonline.com","no-reply-contract-notes@reportsmailer.zerodha.net"]
}

