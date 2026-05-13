import os
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'ACb9c4038dd24b10716cd46262e2e9069d')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'ac35c789c3f15065c553e892df23fb13')
TWILIO_PHONE_NUMBER = 'whatsapp:+14155238886'

def dispatch_sms(to_number: str, message_body: str):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"WhatsApp alert sent: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        return False
