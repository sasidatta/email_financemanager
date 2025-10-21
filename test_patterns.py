#!/usr/bin/env python3
"""
Pattern testing utility for fine-tuning transaction regex patterns.
"""

import re
from patterns import bank_regex_patterns, select_best_pattern
from data import extract_transaction_data

def test_pattern(pattern_name, sample_text, expected_fields=None):
    """Test a specific pattern against sample text."""
    print(f"\n{'='*60}")
    print(f"Testing Pattern: {pattern_name}")
    print(f"{'='*60}")
    
    pattern_data = bank_regex_patterns.get(pattern_name)
    if not pattern_data:
        print(f"Pattern '{pattern_name}' not found!")
        return
    
    pattern = pattern_data["pattern"]
    fields = pattern_data["fields"]
    
    print(f"Sample Text:\n{sample_text}")
    print(f"\nExpected Fields: {fields}")
    
    # Test the pattern
    match = pattern.search(sample_text)
    if match:
        print(f"\n✅ MATCH FOUND!")
        print(f"Match groups: {match.groups()}")
        
        # Extract data
        data = {}
        for idx, field in enumerate(fields):
            try:
                data[field] = match.group(idx + 1)
            except IndexError:
                data[field] = ""
        
        # Add static fields
        for k, v in pattern_data.items():
            if k not in ("pattern", "fields"):
                data[k] = v
        
        print(f"\nExtracted Data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
            
        # Test with extract_transaction_data
        print(f"\nTesting with extract_transaction_data:")
        result = extract_transaction_data(sample_text, "Test Subject")
        if result:
            print(f"✅ Transaction data extracted successfully!")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"❌ No transaction data extracted")
            
    else:
        print(f"\n❌ NO MATCH FOUND!")
        
        # Try to find partial matches
        print(f"\nTrying to find partial matches...")
        for field in fields:
            if field == "amount":
                amount_match = re.search(r'(?:Rs\.?|₹|INR)\s*([\d,]+\.\d{2})', sample_text, re.IGNORECASE)
                if amount_match:
                    print(f"  Found amount: {amount_match.group(1)}")
            elif field == "date":
                date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', sample_text)
                if date_match:
                    print(f"  Found date: {date_match.group(1)}")

def test_all_patterns(sample_text):
    """Test all patterns against sample text."""
    print(f"\n{'='*80}")
    print(f"Testing ALL Patterns")
    print(f"{'='*80}")
    
    pattern_name, match = select_best_pattern(sample_text)
    if pattern_name and match:
        print(f"✅ Best match: {pattern_name}")
        test_pattern(pattern_name, sample_text)
    else:
        print(f"❌ No pattern matched!")
        
        # Test each pattern individually
        for pattern_name in bank_regex_patterns.keys():
            test_pattern(pattern_name, sample_text)

# Sample email texts for testing
SAMPLE_EMAILS = {
    "HDFC_UPI": """❗  You have done a UPI txn. Check details!
    
    Rs. 349.00 has been debited from your HDFC Bank RuPay Credit Card XX7296 to svrcolonykurnool.61857329@hdfcbank SVR COLONY KURNOOL on 20-08-25. Your UPI transaction reference number is 290708328340.""",
    
    "ICICI_CREDIT_CARD": """ICICI Bank Online
    Dear Customer,
    Your ICICI Bank Credit Card XX1039 has been used for a transaction of INR 149.00 on May 09, 2025 at 06:05:07.
    Info: IND*Amazon.
    The Available Credit Limit on your card is INR 1,98,322.31 and Total Credit Limit is INR 4,50,000.00.""",
    
    "KOTAK_IMPS_DEBIT": """Dear BITRA SASI DATTA,
    We wish to inform you that your account xx0381 is debited for Rs. 30000.00 on 09-May-2025 towards IMPS.
    Please find the details as below:
    Beneficiary Name: SAMUDRAPU SUMAVANTH NAGA RAVI BABU
    Beneficiary Account No: XX1551
    Beneficiary IFSC: UTIB0000027
    IMPS Reference No: 512909933692
    Remarks: TO KALYANI""",
    
    "SBI_CREDIT_CARD": """Rs. 1,250.00 spent on your SBI Credit Card ending 1234 at AMAZON INDIA on 15/08/25""",
    
    "AXIS_UPI": """Amount Debited: INR 500.00
    Account Number: XX1234
    Date & Time: 20-08-25, 14:30:25 IST
    Transaction Info: UPI/P2A/1234567890/AMAZON
    If this transaction was not initiated by you:"""
}

def main():
    """Main testing function."""
    print("Pattern Testing Utility")
    print("=" * 50)
    
    while True:
        print(f"\nOptions:")
        print(f"1. Test specific pattern")
        print(f"2. Test all patterns with sample")
        print(f"3. Test custom email text")
        print(f"4. List all patterns")
        print(f"5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            print(f"\nAvailable patterns:")
            for i, pattern_name in enumerate(bank_regex_patterns.keys(), 1):
                print(f"  {i}. {pattern_name}")
            
            try:
                pattern_idx = int(input("\nEnter pattern number: ")) - 1
                pattern_name = list(bank_regex_patterns.keys())[pattern_idx]
                
                print(f"\nSample emails:")
                for i, (name, text) in enumerate(SAMPLE_EMAILS.items(), 1):
                    print(f"  {i}. {name}")
                
                sample_idx = int(input("\nEnter sample number: ")) - 1
                sample_name = list(SAMPLE_EMAILS.keys())[sample_idx]
                sample_text = SAMPLE_EMAILS[sample_name]
                
                test_pattern(pattern_name, sample_text)
                
            except (ValueError, IndexError):
                print("Invalid input!")
                
        elif choice == "2":
            print(f"\nSample emails:")
            for i, (name, text) in enumerate(SAMPLE_EMAILS.items(), 1):
                print(f"  {i}. {name}")
            
            try:
                sample_idx = int(input("\nEnter sample number: ")) - 1
                sample_name = list(SAMPLE_EMAILS.keys())[sample_idx]
                sample_text = SAMPLE_EMAILS[sample_name]
                
                test_all_patterns(sample_text)
                
            except (ValueError, IndexError):
                print("Invalid input!")
                
        elif choice == "3":
            print(f"\nEnter your email text (press Enter twice to finish):")
            lines = []
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
            
            custom_text = "\n".join(lines)
            if custom_text.strip():
                test_all_patterns(custom_text)
            else:
                print("No text entered!")
                
        elif choice == "4":
            print(f"\nAvailable patterns:")
            for i, (pattern_name, pattern_data) in enumerate(bank_regex_patterns.items(), 1):
                print(f"  {i}. {pattern_name}")
                print(f"     Fields: {pattern_data['fields']}")
                print(f"     Type: {pattern_data.get('transactiontype', 'Unknown')}")
                print()
                
        elif choice == "5":
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()
