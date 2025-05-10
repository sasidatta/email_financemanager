import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def handle_upi_email(subject, body, email_data):
    try:

        # Write the email body content to body.txt for later analysis
        with open("body.txt", "a", encoding="utf-8") as f:
           f.write(f"Subject: {subject}\n")
           f.write(f"Body: {body}\n\n")

        # Extract amount
        amount_match = re.search(r"Rs\.?([\d,]+\.\d{2})", body)
        if amount_match:
            email_data["amount"] = amount_match.group(1).replace(",", "")
        else:
            logger.warning("No amount found in email: %s", subject)

        # Extract card info
        card_match = re.search(r"Card\s+(?:Number\s+)?(?:XX)?(\d{4})", body)
        if not card_match:
            card_match = re.search(r"Credit Card\s+XX(\d{4})", body)
        if card_match:
            email_data["card_info"] = card_match.group(1)
        else:
            logger.warning("No card info found in email: %s", subject)

        # Extract merchant or payee
        merchant_match = re.search(r"to\s+([\w@.]+)", body)
        if merchant_match:
            email_data["merchant"] = merchant_match.group(1)
        else:
            logger.warning("No merchant information found in email: %s", subject)

        # Extract UPI reference number
        ref_match = re.search(r"reference number is (\d+)", body)
        if ref_match:
            email_data["reference"] = ref_match.group(1)
        else:
            logger.warning("No reference number found in email: %s", subject)

        # Extract date in DD-MM-YY format and convert to ISO format
        date_match = re.search(r"on (\d{2}-\d{2}-\d{2})", body)
        if date_match:
            try:
                parsed_date = datetime.strptime(date_match.group(1), "%d-%m-%y")
                email_data["txn_date"] = parsed_date.date().isoformat()
            except ValueError:
                logger.warning("Failed to parse date: %s", date_match.group(1))
        else:
            logger.warning("No transaction date found in email: %s", subject)

        logger.info("UPI Email Parsed Data for subject '%s': %s", subject, email_data)

    except Exception as e:
        logger.error("Error processing UPI email for subject '%s': %s", subject, e)
        email_data["error"] = f"Failed to process UPI email: {str(e)}"

    return email_data