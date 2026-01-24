import hmac
import hashlib
from django.conf import settings


def generate_ws_token(conversation_id, user_id):
    secret = settings.CHAT_HMAC_SECRET.encode()
    message = f"{conversation_id}:{user_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_ws_token(conversation_id, user_id, token):
    expected_token = generate_ws_token(conversation_id, user_id)
    return hmac.compare_digest(expected_token, token)