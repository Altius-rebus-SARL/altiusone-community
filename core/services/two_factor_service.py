# core/services/two_factor_service.py
"""
Service pour l'authentification à deux facteurs (TOTP).
Gère la génération de QR codes et les tokens temporaires.
"""
import io
import base64
import hashlib
import hmac
import time

from django.conf import settings

# Token temporaire 2FA: durée de vie en secondes (5 minutes)
TWO_FACTOR_TEMP_TOKEN_EXPIRY = 300


def generate_qr_code_base64(uri):
    """Génère un QR code en base64 à partir d'une URI otpauth://."""
    import qrcode
    img = qrcode.make(uri, box_size=6, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def create_temp_2fa_token(user_id):
    """
    Crée un token temporaire signé pour le challenge 2FA.
    Format: user_id:timestamp:signature
    """
    timestamp = str(int(time.time()))
    user_id_str = str(user_id)
    payload = f"{user_id_str}:{timestamp}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    return f"{user_id_str}:{timestamp}:{signature}"


def verify_temp_2fa_token(token):
    """
    Vérifie un token temporaire 2FA.
    Retourne le user_id si valide, None sinon.
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        user_id_str, timestamp_str, signature = parts

        # Vérifier l'expiration
        timestamp = int(timestamp_str)
        if time.time() - timestamp > TWO_FACTOR_TEMP_TOKEN_EXPIRY:
            return None

        # Vérifier la signature
        payload = f"{user_id_str}:{timestamp_str}"
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()[:32]

        if not hmac.compare_digest(signature, expected):
            return None

        return user_id_str
    except (ValueError, AttributeError):
        return None
