# core/views/mcp_views.py
"""Views for MCP (AI integration) configuration page."""
import secrets
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework.authtoken.models import Token


@login_required
def mcp_setup_view(request):
    """MCP configuration page: token management + setup instructions."""
    token = Token.objects.filter(user=request.user).first()
    base_url = request.build_absolute_uri("/mcp/")

    return render(request, "core/configuration/mcp_setup.html", {
        "token": token,
        "mcp_url": base_url,
        "mcp_sse_url": base_url + "sse/",
    })


@login_required
@require_POST
def mcp_generate_token(request):
    """Generate or regenerate an API token for MCP."""
    Token.objects.filter(user=request.user).delete()
    token = Token.objects.create(user=request.user)
    return JsonResponse({"token": token.key})


@login_required
@require_POST
def mcp_revoke_token(request):
    """Revoke the user's API token."""
    Token.objects.filter(user=request.user).delete()
    return JsonResponse({"ok": True})
