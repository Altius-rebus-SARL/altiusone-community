# core/ai/__init__.py
"""
Module IA local pour AltiusOne.

Tout le traitement IA tourne en local sur chaque instance:
- Embeddings: sentence-transformers (768D, multilingue)
- Chat LLM: Ollama (phi3:mini, tool calling)
- OCR: Tesseract (déjà dans documents/ai_service.py)
"""
