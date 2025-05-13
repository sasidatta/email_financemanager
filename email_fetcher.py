import imaplib
import os
from dotenv import load_dotenv
from config_loader import Config

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