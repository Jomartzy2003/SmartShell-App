import os
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'mock_sid')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'mock_token')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')

def dispatch_sms(to_number: str, message_body: str):
    if TWILIO_ACCOUNT_SID == 'mock_sid':
        logger.info(f"[MOCK SMS] to {to_number}: {message_body}")
        print(f"\n{'='*40}\n[MOCK SMS] to {to_number}:\n{message_body}\n{'='*40}\n")
        return True
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info(f"SMS dispatched: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False
