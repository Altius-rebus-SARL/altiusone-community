# analytics/services/__init__.py
"""
Services pour l'application Analytics.

Ce module contient les services métier séparés pour une meilleure organisation:
- rapport_section_service: Gestion des sections de rapport
- graphique_service: Génération des données de graphiques
- pdf_service: Génération des PDF
"""

from .rapport_section_service import RapportSectionService
from .graphique_service import GraphiqueService

__all__ = [
    'RapportSectionService',
    'GraphiqueService',
]
