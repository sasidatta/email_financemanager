#!/usr/bin/env python3
"""
Debug script to analyze email processing and pattern matching.
"""

import os
import sys
from dotenv import load_dotenv
from email_fetcher import connect_to_imap, fetch_emails
from extract_mail_data import parse_email_content, extract_transaction_data, should_skip_email
from patterns import select_best_pattern, bank_regex_patterns

load_dotenv()

def analyze_emails(n_days=1):
    """Analyze emails to understand pattern matching."""
    try:
        # Connect to IMAP
        imap = connect_to_imap()
        
        # Fetch emails
        raw_emails = fetch_emails(imap, n_days=n_days, keywords=[
            "transaction", "debited", "credited", "upi", "imps", "neft",
            "credit card", "debit card", "spent", "payment", "paid"
        ])
        
        print(f"Fetched {len(raw_emails)} emails")
        print("=" * 80)
        
        from email.parser import BytesParser
        from email import policy
        
        for i, raw_bytes in enumerate(raw_emails):
            try:
                msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
                subject, body, sender_email = parse_email_content(raw_bytes)
                
                print(f"\nEmail {i+1}:")
                print(f"Subject: {subject}")
                print(f"From: {sender_email}")
                print(f"Body preview: {body[:200]}...")
                
                # Check if should be skipped
                if should_skip_email(subject, body):
                    print("❌ SKIPPED (non-transactional)")
                    continue
                
                # Test pattern matching
                pattern_name, match = select_best_pattern(body)
                if pattern_name and match:
                    print(f"✅ Pattern matched: {pattern_name}")
                    print(f"   Match groups: {match.groups()}")
                    
                    # Extract transaction data
                    txn_data = extract_transaction_data(body, subject)
                    if txn_data:
                        print(f"✅ Transaction extracted:")
                        for key, value in txn_data.items():
                            print(f"   {key}: {value}")
                    else:
                        print("❌ No transaction data extracted")
                else:
                    print("❌ No pattern matched")
                    
                    # Show what we found
                    import re
                    amount_match = re.search(r'(?:Rs\.?|₹|INR)\s*([\d,]+\.\d{2})', body, re.IGNORECASE)
                    if amount_match:
                        print(f"   Found amount: {amount_match.group(1)}")
                    
                    date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', body)
                    if date_match:
                        print(f"   Found date: {date_match.group(1)}")
                
                print("-" * 60)
                
            except Exception as e:
                print(f"Error processing email {i+1}: {e}")
                continue
        
        imap.logout()
        
    except Exception as e:
        print(f"Error: {e}")

def test_pattern_with_email(pattern_name, email_text):
    """Test a specific pattern with email text."""
    pattern_data = bank_regex_patterns.get(pattern_name)
    if not pattern_data:
        print(f"Pattern '{pattern_name}' not found!")
        return
    
    pattern = pattern_data["pattern"]
    match = pattern.search(email_text)
    
    print(f"Testing pattern: {pattern_name}")
    print(f"Email text: {email_text[:200]}...")
    
    if match:
        print(f"✅ MATCH!")
        print(f"Groups: {match.groups()}")
        
        # Extract data
        data = {}
        for idx, field in enumerate(pattern_data["fields"]):
            try:
                data[field] = match.group(idx + 1)
            except IndexError:
                data[field] = ""
        
        print(f"Extracted data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print("❌ NO MATCH")

def main():
    """Main function."""
    print("Email Debug Utility")
    print("=" * 50)
    
    while True:
        print(f"\nOptions:")
        print(f"1. Analyze recent emails")
        print(f"2. Test pattern with custom text")
        print(f"3. List all patterns")
        print(f"4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            try:
                n_days = int(input("Enter number of days to analyze (default 1): ") or "1")
                analyze_emails(n_days)
            except ValueError:
                print("Invalid input!")
                
        elif choice == "2":
            print(f"\nAvailable patterns:")
            for i, pattern_name in enumerate(bank_regex_patterns.keys(), 1):
                print(f"  {i}. {pattern_name}")
            
            try:
                pattern_idx = int(input("\nEnter pattern number: ")) - 1
                pattern_name = list(bank_regex_patterns.keys())[pattern_idx]
                
                print(f"\nEnter email text (press Enter twice to finish):")
                lines = []
                while True:
                    line = input()
                    if line == "" and lines:
                        break
                    lines.append(line)
                
                email_text = "\n".join(lines)
                if email_text.strip():
                    test_pattern_with_email(pattern_name, email_text)
                else:
                    print("No text entered!")
                    
            except (ValueError, IndexError):
                print("Invalid input!")
                
        elif choice == "3":
            print(f"\nAvailable patterns:")
            for i, (pattern_name, pattern_data) in enumerate(bank_regex_patterns.items(), 1):
                print(f"  {i}. {pattern_name}")
                print(f"     Fields: {pattern_data['fields']}")
                print(f"     Type: {pattern_data.get('transactiontype', 'Unknown')}")
                print()
                
        elif choice == "4":
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()
