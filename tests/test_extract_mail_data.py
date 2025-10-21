import pytest
from data import extract_transaction_data

ICICI_SAMPLE = '''ICICI Bank Online Dear Customer, Your ICICI Bank Credit Card XX1039 has been used for a transaction of INR 149.00 on May 09, 2025 at 06:05:07. Info: IND*Amazon. The Available Credit Limit on your card is INR 1,98,322.31 and Total Credit Limit is INR 4,50,000.00.'''

KOTAK_IMPS_DEBIT_SAMPLE = '''Dear BITRA SASI DATTA,We wish to inform you that your account xx0381 is debited for Rs. 30000.00 on 09-May-2025 towards IMPS. Please find the details as below: Beneficiary Name: SAMUDRAPU SUMAVANTH NAGA RAVI BABU Beneficiary Account No: XX1551 Beneficiary IFSC: UTIB0000027 IMPS Reference No: 512909933692Remarks: TO KALYANI'''

AXIS_EMI_SAMPLE = '''10-05-2025 Dear Bitra Sasi Datta, Thank you for banking with us. We wish to inform you that your A/c no. XX3438 has been debited with INR 12329.00 on 10-05-2025 09:31:13 IST by PPR006912066737_EMI_10-05-.'''

NON_TXN_SAMPLE = '''ASIAN PAINTS LIMITED CIN: L24220MH1945PLC004598 Registered Office: 6A & 6B, Shantinagar, Santacruz (East), Mumbai – 400 055, Maharashtra, India Email: investor.relations@asianpaints.com, Website: www.asianpaints.com Tel No.: (022) 6218 1000 Date: 9th May 2025 Dear Shareholder(s), We are pleased to inform you that the Board of Directors of the Company at their meeting held on Thursday, 8th May 2025 have, inter alia, approved and recommended payment of final dividend of Rs. 20.55 (Rupees twenty and paise fifty-five only) per equity share of face value of Re. 1 (Rupee one) each fully paid up for the financial year ended 31st March 2025 (‘Final Dividend’), subject to approval of shareholders at the ensuing 79th Annual General Meeting (‘AGM’) of the Company to be held on Thursday, 26th June 2025.'''

def test_icici_credit_card():
    data = extract_transaction_data(ICICI_SAMPLE)
    assert data is not None
    assert data["card_number"] == "XX1039"
    assert data["amount"] == 149.00
    assert data["merchant_name"].startswith("IND*Amazon")
    assert data["transactiontype"].lower() == "credit card"
    assert data["date"] == "2025-05-09"

def test_kotak_imps_debit():
    data = extract_transaction_data(KOTAK_IMPS_DEBIT_SAMPLE)
    assert data is not None
    assert data["amount"] == 30000.00
    assert data["beneficiary_name"].startswith("SAMUDRAPU SUMAVANTH")
    assert data["transactiontype"].lower() == "imps debit"
    assert data["date"] == "2025-05-09"

def test_axis_emi_debit():
    data = extract_transaction_data(AXIS_EMI_SAMPLE)
    assert data is not None
    assert data["amount"] == 12329.00
    assert data["account_number"].startswith("XX3438")
    assert data["transactiontype"].lower() == "emi debit"
    assert data["date"] == "2025-05-10"

def test_non_transaction_email():
    data = extract_transaction_data(NON_TXN_SAMPLE)
    assert data is None 