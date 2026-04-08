# core/ai/chat.py
"""
Service de chat local via transformers (Hugging Face).

Charge le modèle directement en mémoire Python — pas de container Ollama.
Même pattern que LocalEmbeddingService (lazy loading, singleton).

Modèle par défaut: Qwen/Qwen2.5-0.5B-Instruct (~500MB RAM)
- Suffisant pour reformuler des résultats pgvector en langage naturel
- Multilingue FR/DE/EN/IT
- Le raisonnement complexe est fait par pgvector, pas par le LLM
"""
import logging
import time
import threading
from typing import Any, Dict, Generator, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Lock pour éviter les accès concurrents au modèle (pas thread-safe)
_model_lock = threading.Lock()


class LocalChatService:
    """
    Service de chat local avec transformers.

    Le modèle est chargé lazily au premier appel et gardé en mémoire.
    Expose la même interface que l'ancien OllamaChatService.
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._model_name = getattr(
            settings, 'CHAT_MODEL_NAME', 'Qwen/Qwen2.5-0.5B-Instruct'
        )
        self._max_new_tokens = getattr(settings, 'CHAT_MAX_NEW_TOKENS', 300)

    def _load_model(self):
        """Charge le modèle et le tokenizer (une seule fois)."""
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info(f"Chargement du modèle chat: {self._model_name}")
        start = time.time()

        self._tokenizer = AutoTokenizer.from_pretrained(
            self._model_name,
            trust_remote_code=True,
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_name,
            torch_dtype=torch.float16,
            device_map="cpu",
            trust_remote_code=True,
        )
        self._model.eval()

        elapsed = time.time() - start
        logger.info(f"Modèle chat chargé en {elapsed:.1f}s")

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        """Vérifie si le modèle peut être chargé."""
        try:
            self._load_model()
            return self._model is not None
        except Exception as e:
            logger.error(f"Modèle chat non disponible: {e}")
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
        Génère une réponse (non-streaming).

        Même interface que l'ancien OllamaChatService.chat().
        Le paramètre tools est ignoré (plus de tool calling).
        """
        self._load_model()

        messages = self._build_messages(
            message, system, system_prompt, context, history, messages_override
        )

        start = time.time()
        max_new = max_tokens or self._max_new_tokens

        try:
            with _model_lock:
                response_text = self._generate(messages, temperature, max_new)

            elapsed_ms = int((time.time() - start) * 1000)

            return {
                'response': response_text,
                'tokens_prompt': 0,
                'tokens_completion': len(response_text.split()),
                'processing_time_ms': elapsed_ms,
            }

        except Exception as e:
            logger.error(f"Erreur chat: {e}")
            raise ChatError(str(e))

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
        Génère une réponse en streaming (token par token).

        Utilise TextIteratorStreamer de transformers.
        """
        self._load_model()

        messages = self._build_messages(
            message, system, system_prompt, context, history, messages_override
        )

        max_new = max_tokens or self._max_new_tokens
        start = time.time()

        try:
            from transformers import TextIteratorStreamer

            text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self._tokenizer(text, return_tensors="pt")
            input_len = inputs["input_ids"].shape[1]

            streamer = TextIteratorStreamer(
                self._tokenizer, skip_prompt=True, skip_special_tokens=True
            )

            # Lancer la génération dans un thread (le streamer bloque sinon)
            import torch
            gen_kwargs = {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "max_new_tokens": max_new,
                "temperature": max(temperature, 0.01),
                "do_sample": temperature > 0,
                "streamer": streamer,
            }

            thread = threading.Thread(
                target=self._generate_threaded,
                args=(gen_kwargs,),
            )
            thread.start()

            total_tokens = 0
            for token_text in streamer:
                if token_text:
                    total_tokens += 1
                    yield {
                        'type': 'token',
                        'token': token_text,
                    }

            thread.join()

            yield {
                'type': 'done',
                'done': True,
                'model': self._model_name,
                'tokens_used': total_tokens,
                'processing_time_ms': int((time.time() - start) * 1000),
            }

        except Exception as e:
            logger.error(f"Erreur chat stream: {e}")
            yield {'type': 'error', 'error': str(e)}

    def _generate(self, messages: List[Dict], temperature: float, max_new_tokens: int) -> str:
        """Génère une réponse complète (bloquant)."""
        import torch

        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            outputs = self._model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_new_tokens,
                temperature=max(temperature, 0.01),
                do_sample=temperature > 0,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        # Décoder uniquement les tokens générés (pas le prompt)
        input_len = inputs["input_ids"].shape[1]
        response = self._tokenizer.decode(
            outputs[0][input_len:], skip_special_tokens=True
        )
        return response.strip()

    def _generate_threaded(self, gen_kwargs):
        """Wrapper pour model.generate dans un thread (pour le streaming)."""
        import torch
        with _model_lock:
            with torch.no_grad():
                self._model.generate(**gen_kwargs)

    def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état du service chat."""
        return {
            'enabled': True,
            'backend': 'transformers',
            'model': self._model_name,
            'model_loaded': self._model is not None,
        }

    def _build_messages(
        self,
        message: str,
        system: Optional[str],
        system_prompt: Optional[str],
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
        messages_override: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, str]]:
        """Construit la liste de messages pour le modèle."""
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


class ChatError(Exception):
    """Erreur du service chat local."""
    pass


# Singleton
chat_service = LocalChatService()
