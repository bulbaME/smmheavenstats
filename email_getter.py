import email
import imaplib
import yaml
from time import time

CRED = yaml.safe_load(open('credentials.yaml'))['MAIL']

EMAIL = CRED['NAME']
PASSWORD = CRED['PSW']
SERVER = 'mail.seodigital360.com'
MAX_WAIT_TIME = 60

def get_mail_code():
    mail = imaplib.IMAP4_SSL(SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select('inbox')
    tf = time()

    print('[retrieving passcode]')

    while True:
        status, data = mail.search(None, '(UNSEEN)')
        mail_ids = []

        tl = time()
        if (tf + MAX_WAIT_TIME < tl): break

        for block in data:
            mail_ids += block.split()

        if len(mail_ids) == 0:
            continue

        _, data = mail.fetch(mail_ids[0], '(RFC822)')
        for response_part in data:
                if isinstance(response_part, tuple):
                    message = email.message_from_bytes(response_part[1])
                    if message['sender'] == 'noreply@mail-smm.com':
                        msg = message.get_payload()
                        psw = msg.split(':')[1].strip()
                        
                        return int(psw)
                    
    return 100000