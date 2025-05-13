import imaplib
from config_loader import Config

config = Config()
email_conf = config.email

EMAIL = email_conf.get('address')
PASSWORD = email_conf.get('password')
IMAP_SERVER = email_conf.get('imap_server')

def connect_to_imap(server=None):
    server = server or IMAP_SERVER
    imap = imaplib.IMAP4_SSL(server)
    imap.login(EMAIL, PASSWORD)
    imap.select("INBOX")
    return imap 