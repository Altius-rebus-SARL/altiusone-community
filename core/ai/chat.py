# core/ai/chat.py
"""
Service de chat local via Ollama.

Modèle par défaut: qwen2.5:3b (3B, ~1.9GB)
- Supporte tool calling (format OpenAI-compatible)
- Multilingue FR/DE/EN/IT (même famille que l'ancien SDK Qwen 2.5 14B)
- Streaming SSE token par token

L'API Ollama est compatible OpenAI :
- POST /api/chat (non-streaming + streaming)
"""
import json
import logging
from typing import Any, Dict, Generator, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaChatService:
    """
    Service de chat local via Ollama.

    Expose la même interface que l'ancien AltiusAIService.chat()
    pour une migration transparente.
    """

    def __init__(self):
        self._base_url = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        self._model = getattr(settings, 'OLLAMA_CHAT_MODEL', 'qwen2.5:3b')
        self._timeout = getattr(settings, 'OLLAMA_TIMEOUT', 120)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_available(self) -> bool:
        """Vérifie si Ollama est joignable et le modèle est chargé."""
        try:
            resp = requests.get(
                f"{self._base_url}/api/tags",
                timeout=5,
            )
            if resp.status_code != 200:
                return False
            models = [m['name'] for m in resp.json().get('models', [])]
            # Vérifier que le modèle (ou un préfixe) est présent
            return any(self._model in m for m in models)
        except Exception:
            return False

    def pull_model(self) -> bool:
        """Télécharge le modèle si absent. Bloquant."""
        try:
            logger.info(f"Pull du modèle Ollama: {self._model}")
            resp = requests.post(
                f"{self._base_url}/api/pull",
                json={'name': self._model, 'stream': False},
                timeout=600,  # 10 min pour le premier téléchargement
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Erreur pull modèle Ollama: {e}")
            return False

    def chat(
        self,
        message: str = "",
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        messages_override: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Envoie un message au LLM local (non-streaming).

        Interface identique à l'ancien AltiusAIService.chat().

        Returns:
            Dict avec 'response', 'tokens_prompt', 'tokens_completion',
            et optionnel 'tool_calls'
        """
        messages = self._build_messages(
            message, system, system_prompt, context, history, messages_override
        )

        request_data: Dict[str, Any] = {
            'model': self._model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_ctx': 2048,  # Limiter le contexte pour éviter OOM sur 8GB
            },
        }
        if max_tokens:
            request_data['options']['num_predict'] = max_tokens
        if tools:
            request_data['tools'] = tools

        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=request_data,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            msg = data.get('message', {})
            response_text = msg.get('content', '')

            result: Dict[str, Any] = {
                'response': response_text,
                'tokens_prompt': data.get('prompt_eval_count', 0),
                'tokens_completion': data.get('eval_count', 0),
            }

            # Tool calls (Ollama format)
            tool_calls = msg.get('tool_calls')
            if tool_calls:
                # Normaliser au format OpenAI-compatible
                normalized = []
                for tc in tool_calls:
                    func = tc.get('function', {})
                    normalized.append({
                        'id': f"call_{len(normalized)}",
                        'type': 'function',
                        'function': {
                            'name': func.get('name', ''),
                            'arguments': func.get('arguments', {}),
                        }
                    })
                result['tool_calls'] = normalized

            return result

        except requests.exceptions.ConnectionError:
            logger.error(f"Ollama non joignable: {self._base_url}")
            raise OllamaChatError(f"Impossible de se connecter à Ollama ({self._base_url})")
        except requests.exceptions.Timeout:
            raise OllamaChatError(f"Ollama timeout ({self._timeout}s)")
        except requests.exceptions.HTTPError as e:
            raise OllamaChatError(f"Erreur Ollama HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Erreur chat Ollama: {e}")
            raise OllamaChatError(str(e))

    def chat_stream(
        self,
        message: str = "",
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        messages_override: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream la réponse token par token.

        Interface identique à l'ancien AltiusAIService.chat_stream().

        Yields:
            Dict avec 'type': 'token'|'done'|'error' et données associées
        """
        messages = self._build_messages(
            message, system, system_prompt, context, history, messages_override
        )

        request_data: Dict[str, Any] = {
            'model': self._model,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_ctx': 2048,
            },
        }
        if max_tokens:
            request_data['options']['num_predict'] = max_tokens
        # Pas de tools en streaming (Ollama ne supporte pas tools + stream ensemble)
        # Les tools sont gérés en non-streaming par chat_service.py

        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=request_data,
                stream=True,
                timeout=self._timeout,
            )
            resp.raise_for_status()

            total_tokens = 0
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if data.get('done'):
                    total_tokens = data.get('eval_count', 0)
                    yield {
                        'type': 'done',
                        'done': True,
                        'model': data.get('model', self._model),
                        'tokens_used': total_tokens,
                        'processing_time_ms': int(data.get('total_duration', 0) / 1_000_000),
                    }
                    return

                msg = data.get('message', {})
                token = msg.get('content', '')
                if token:
                    yield {
                        'type': 'token',
                        'token': token,
                    }

        except requests.exceptions.ConnectionError:
            yield {'type': 'error', 'error': f"Ollama non joignable ({self._base_url})"}
        except requests.exceptions.Timeout:
            yield {'type': 'error', 'error': f"Ollama timeout ({self._timeout}s)"}
        except Exception as e:
            logger.error(f"Erreur chat stream Ollama: {e}")
            yield {'type': 'error', 'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état d'Ollama."""
        status: Dict[str, Any] = {
            'enabled': True,
            'backend': 'ollama',
            'url': self._base_url,
            'model': self._model,
            'connected': False,
            'model_loaded': False,
        }
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                status['connected'] = True
                models = [m['name'] for m in resp.json().get('models', [])]
                status['model_loaded'] = any(self._model in m for m in models)
                status['available_models'] = models
        except Exception as e:
            status['error'] = str(e)
        return status

    def _build_messages(
        self,
        message: str,
        system: Optional[str],
        system_prompt: Optional[str],
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
        messages_override: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, str]]:
        """Construit la liste de messages pour l'API Ollama."""
        if messages_override:
            return messages_override

        system = system or system_prompt
        if context:
            message = f"Contexte:\n{context}\n\nQuestion: {message}"

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({'role': 'system', 'content': system})

        if history:
            for msg in history[:-1] if history else []:
                role = msg.get('role', '').lower()
                content = msg.get('content', '')
                if role in ('user', 'assistant') and content:
                    messages.append({'role': role, 'content': content})

        if message:
            messages.append({'role': 'user', 'content': message})

        return messages


class OllamaChatError(Exception):
    """Erreur du service chat Ollama."""
    pass


# Singleton
chat_service = OllamaChatService()
