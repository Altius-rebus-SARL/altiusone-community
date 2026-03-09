# mcp/auth.py
"""JWT authentication for MCP endpoints."""
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

_jwt_auth = JWTAuthentication()


def authenticate_request(request):
    """
    Authenticate an MCP request using JWT Bearer token.
    Returns (user, error_dict). If auth fails, user is None.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None, {
            "code": -32000,
            "message": "Authentication required. Send Authorization: Bearer <jwt_token>",
        }

    try:
        validated = _jwt_auth.authenticate(request)
        if validated is None:
            return None, {"code": -32000, "message": "Invalid token"}
        user, _token = validated
        if not user.is_active:
            return None, {"code": -32000, "message": "User account is disabled"}
        return user, None
    except (InvalidToken, TokenError) as e:
        return None, {"code": -32000, "message": f"Token error: {e}"}
    except Exception as e:
        logger.error(f"MCP auth error: {e}")
        return None, {"code": -32000, "message": "Authentication failed"}
