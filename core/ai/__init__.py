# core/ai/__init__.py
"""
Module IA local pour AltiusOne.

Tout le traitement IA tourne en local sur chaque instance:
- Embeddings: sentence-transformers (768D, multilingue)
- Chat LLM: transformers direct (Qwen2.5-0.5B-Instruct, ~500MB RAM)
- OCR: Tesseract (déjà dans documents/ai_service.py)
"""
