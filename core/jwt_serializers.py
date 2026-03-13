# core/jwt_serializers.py
"""
Custom JWT Serializers for AltiusOne Mobile App
Returns user data along with JWT tokens for mobile authentication.
Supports 2FA challenge flow: if user has 2FA enabled, returns a temp_token
instead of JWT tokens; the client must then POST to /api/v1/auth/2fa/verify/.
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes user data in the response.
    Mobile app expects: { access, refresh, user: { id, email, name, ... } }

    If 2FA is enabled:
    Returns: { requires_2fa: true, temp_token: "..." } (no JWT tokens)
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims to token
        token['email'] = user.email
        token['name'] = user.get_full_name() or user.username
        if hasattr(user, 'company_name'):
            token['company'] = user.company_name

        return token

    def validate(self, attrs):
        # Authenticate user (calls super which sets self.user)
        data = super().validate(attrs)

        user = self.user

        # 2FA challenge: if enabled, don't return JWT tokens yet
        if user.two_factor_enabled and user.totp_secret:
            from .services.two_factor_service import create_temp_2fa_token
            return {
                'requires_2fa': True,
                'temp_token': create_temp_2fa_token(user.id),
            }

        # Normal flow: return tokens + user data
        data['user'] = self._build_user_data(user)
        return data

    @staticmethod
    def _build_user_data(user):
        """Construit le dict de données utilisateur pour la réponse."""
        user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }

        # Add role and type info
        user_data['role'] = str(user.role_id) if user.role_id else None
        user_data['role_code'] = user.role.code if user.role else None
        user_data['type_utilisateur'] = user.type_utilisateur if hasattr(user, 'type_utilisateur') else None

        # Add company info if available (AltiusOne custom User model)
        if hasattr(user, 'company_name'):
            user_data['company_name'] = user.company_name
        if hasattr(user, 'phone'):
            user_data['phone'] = str(user.phone) if user.phone else None
        if hasattr(user, 'language'):
            user_data['language'] = user.language

        return user_data


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Serializer for token refresh response documentation"""
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)
