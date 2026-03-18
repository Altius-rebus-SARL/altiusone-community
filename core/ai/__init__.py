# core/ai/__init__.py
"""
Module IA local pour AltiusOne.

Tout le traitement IA tourne en local sur chaque instance:
- Embeddings: sentence-transformers (768D, multilingue)
- Chat LLM: Ollama (qwen2.5:3b, tool calling)
- OCR: Tesseract (déjà dans documents/ai_service.py)
"""
