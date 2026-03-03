# core/import_export/__init__.py
"""
Package d'import/export pour AltiusOne.

Ce package fournit une couche d'abstraction au-dessus de django-import-export
pour permettre l'import/export de données avec des identifiants naturels
(au lieu des UUID) et une validation stricte par Mandat.

Fonctionnalités:
- Widgets personnalisés pour résoudre les FK par identifiants naturels
- Validation automatique des accès aux Mandats
- Logging dans AuditLog
- Mode dry-run (simulation)
- Templates vides téléchargeables
- Support multilingue (FR/DE/IT/EN)
"""

from .widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    MultiFieldLookupWidget,
    DateWidget,
    DecimalWidget,
    BooleanWidget,
)

from .base import (
    BaseImportExportResource,
    MandatAwareResource,
    AuditedResource,
)

__all__ = [
    # Widgets
    'NaturalKeyForeignKeyWidget',
    'MandatAwareForeignKeyWidget',
    'MultiFieldLookupWidget',
    'DateWidget',
    'DecimalWidget',
    'BooleanWidget',
    # Resources
    'BaseImportExportResource',
    'MandatAwareResource',
    'AuditedResource',
]
