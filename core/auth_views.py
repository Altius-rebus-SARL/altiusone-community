# apps/core/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def simple_login(request):
    """Login simple pour le développement"""
    data = json.loads(request.body) if request.body else request.data
    username = data.get("username")
    password = data.get("password")

    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_superuser": user.is_superuser,
                    "role": getattr(user, "role", "ADMIN"),
                },
            }
        )

    return Response({"success": False, "error": "Invalid credentials"}, status=401)


@api_view(["GET"])
def check_auth(request):
    """Vérifier si l'utilisateur est connecté"""
    if request.user.is_authenticated:
        return Response(
            {
                "authenticated": True,
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "role": getattr(request.user, "role", "ADMIN"),
                },
            }
        )
    return Response({"authenticated": False})


@api_view(["POST"])
def simple_logout(request):
    logout(request)
    return Response({"success": True})
