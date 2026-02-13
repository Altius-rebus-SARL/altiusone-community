# mcp/server.py
"""
Serveur MCP (Model Context Protocol) pour AltiusOne.

Expose le graphe relationnel via SSE (Server-Sent Events) pour
permettre l'intégration avec des clients MCP (Claude, etc.).
"""
import json
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tools import get_tools, execute_tool
from .resources import get_resources, read_resource

logger = logging.getLogger(__name__)

SERVER_INFO = {
    'name': 'altiusone-graph',
    'version': '1.0.0',
    'protocolVersion': '2024-11-05',
    'capabilities': {
        'tools': {},
        'resources': {},
    },
}


@csrf_exempt
@require_http_methods(['POST'])
def mcp_endpoint(request):
    """
    Endpoint JSON-RPC pour le protocole MCP.

    Supporte les méthodes:
    - initialize
    - tools/list
    - tools/call
    - resources/list
    - resources/read
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {'code': -32700, 'message': 'Parse error'},
            'id': None,
        }, status=400)

    method = body.get('method', '')
    params = body.get('params', {})
    request_id = body.get('id')

    result = _handle_method(method, params)

    return JsonResponse({
        'jsonrpc': '2.0',
        'result': result,
        'id': request_id,
    })


def _handle_method(method, params):
    """Route les méthodes MCP."""
    if method == 'initialize':
        return SERVER_INFO

    elif method == 'tools/list':
        return {'tools': get_tools()}

    elif method == 'tools/call':
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})
        result = execute_tool(tool_name, arguments)
        return {
            'content': [
                {'type': 'text', 'text': json.dumps(result, ensure_ascii=False, default=str)},
            ],
        }

    elif method == 'resources/list':
        return {'resources': get_resources()}

    elif method == 'resources/read':
        uri = params.get('uri', '')
        data = read_resource(uri)
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(data, ensure_ascii=False, default=str),
                },
            ],
        }

    else:
        return {'error': {'code': -32601, 'message': f'Method not found: {method}'}}


@csrf_exempt
def mcp_sse_endpoint(request):
    """
    Endpoint SSE pour le transport MCP streamable.

    Le client envoie des requêtes JSON-RPC via POST et reçoit
    les réponses via SSE.
    """
    if request.method == 'POST':
        return mcp_endpoint(request)

    # GET: SSE stream (keep-alive)
    def event_stream():
        yield f'data: {json.dumps({"type": "ready", "server": SERVER_INFO})}\n\n'

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
