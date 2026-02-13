# mcp/urls.py
from django.urls import path
from . import server

app_name = 'mcp'

urlpatterns = [
    path('', server.mcp_endpoint, name='mcp-endpoint'),
    path('sse/', server.mcp_sse_endpoint, name='mcp-sse'),
]
