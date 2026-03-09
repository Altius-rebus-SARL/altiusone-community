# mcp/auth.py
"""Authentication for MCP endpoints. Supports JWT and DRF Token."""
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

_jwt_auth = JWTAuthentication()


def authenticate_request(request):
    """
    Authenticate an MCP request.
    Accepts:
      - Bearer <jwt_token>   (SimpleJWT, short-lived)
      - Token <api_token>    (DRF authtoken, persistent)
    Returns (user, error_dict). If auth fails, user is None.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")

    if auth_header.startswith("Token "):
        return _auth_drf_token(auth_header[6:].strip())
    elif auth_header.startswith("Bearer "):
        return _auth_jwt(request)
    else:
        return None, {
            "code": -32000,
            "message": "Authentication required. Send 'Authorization: Token <api_token>' or 'Authorization: Bearer <jwt>'",
        }


def _auth_jwt(request):
    try:
        validated = _jwt_auth.authenticate(request)
        if validated is None:
            return None, {"code": -32000, "message": "Invalid JWT token"}
        user, _token = validated
        if not user.is_active:
            return None, {"code": -32000, "message": "User account is disabled"}
        return user, None
    except (InvalidToken, TokenError) as e:
        return None, {"code": -32000, "message": f"JWT error: {e}"}
    except Exception as e:
        logger.error(f"MCP JWT auth error: {e}")
        return None, {"code": -32000, "message": "Authentication failed"}


def _auth_drf_token(key):
    try:
        from rest_framework.authtoken.models import Token
        token = Token.objects.select_related("user").get(key=key)
        if not token.user.is_active:
            return None, {"code": -32000, "message": "User account is disabled"}
        return token.user, None
    except Token.DoesNotExist:
        return None, {"code": -32000, "message": "Invalid API token"}
    except Exception as e:
        logger.error(f"MCP token auth error: {e}")
        return None, {"code": -32000, "message": "Authentication failed"}
