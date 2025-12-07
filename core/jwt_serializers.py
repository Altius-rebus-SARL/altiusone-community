# core/jwt_serializers.py
"""
Custom JWT Serializers for AltiusOne Mobile App
Returns user data along with JWT tokens for mobile authentication
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes user data in the response.
    Mobile app expects: { access, refresh, user: { id, email, name, ... } }
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
        data = super().validate(attrs)

        # Add user data to response (mobile app expects this)
        user = self.user
        data['user'] = {
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

        # Add company info if available (AltiusOne custom User model)
        if hasattr(user, 'company_name'):
            data['user']['company_name'] = user.company_name
        if hasattr(user, 'phone'):
            data['user']['phone'] = str(user.phone) if user.phone else None
        if hasattr(user, 'language'):
            data['user']['language'] = user.language

        return data


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Serializer for token refresh response documentation"""
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)
