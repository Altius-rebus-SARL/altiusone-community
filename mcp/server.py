# mcp/server.py
"""
AltiusOne MCP Server (Model Context Protocol).

Full-featured MCP server exposing all business modules via JSON-RPC 2.0.
Requires JWT authentication on every request.
"""
import json
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import authenticate_request
from .tools import get_tools, execute_tool
from .resources import get_resources, read_resource

logger = logging.getLogger(__name__)

SERVER_INFO = {
    "name": "altiusone",
    "version": "2.0.0",
    "protocolVersion": "2024-11-05",
    "capabilities": {
        "tools": {},
        "resources": {},
    },
}


def _error_response(code, message, request_id=None, status=400):
    return JsonResponse(
        {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id},
        status=status,
    )


def _success_response(result, request_id):
    return JsonResponse({"jsonrpc": "2.0", "result": result, "id": request_id})


@csrf_exempt
@require_http_methods(["POST"])
def mcp_endpoint(request):
    """
    JSON-RPC 2.0 endpoint for MCP protocol.

    Methods: initialize, tools/list, tools/call, resources/list, resources/read
    Auth: Bearer JWT token required (except initialize).
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _error_response(-32700, "Parse error", status=400)

    method = body.get("method", "")
    params = body.get("params", {})
    request_id = body.get("id")

    # initialize does not require auth (lets client discover capabilities)
    if method == "initialize":
        return _success_response(SERVER_INFO, request_id)

    # All other methods require authentication
    user, auth_error = authenticate_request(request)
    if auth_error:
        return _error_response(auth_error["code"], auth_error["message"], request_id, status=401)

    result = _handle_method(method, params, user)
    return _success_response(result, request_id)


def _handle_method(method, params, user):
    """Route MCP methods."""
    if method == "tools/list":
        return {"tools": get_tools()}

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = execute_tool(tool_name, arguments, user)
        return {
            "content": [
                {"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)},
            ],
        }

    elif method == "resources/list":
        return {"resources": get_resources()}

    elif method == "resources/read":
        uri = params.get("uri", "")
        data = read_resource(uri, user)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(data, ensure_ascii=False, default=str),
                },
            ],
        }

    return {"error": {"code": -32601, "message": f"Method not found: {method}"}}


@csrf_exempt
def mcp_sse_endpoint(request):
    """
    SSE transport for MCP. GET returns event stream, POST routes to JSON-RPC.
    """
    if request.method == "POST":
        return mcp_endpoint(request)

    def event_stream():
        yield f"data: {json.dumps({'type': 'ready', 'server': SERVER_INFO})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
