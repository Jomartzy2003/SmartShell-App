import os
from twilio.rest import Client
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
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
