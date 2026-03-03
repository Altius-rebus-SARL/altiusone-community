# core/import_export/widgets.py
"""
Widgets personnalisés pour django-import-export.

Ces widgets permettent de résoudre les clés étrangères par des identifiants
naturels (nom, code, référence) au lieu des UUID, rendant l'import/export
accessible aux utilisateurs non-techniques.
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, Optional, Type, List, Dict

from django.db.models import Model, Q
from django.utils.translation import gettext_lazy as _
from django.utils.dateparse import parse_date, parse_datetime

from import_export.widgets import (
    Widget,
    ForeignKeyWidget as BaseForeignKeyWidget,
    ManyToManyWidget as BaseManyToManyWidget,
    DateWidget as BaseDateWidget,
    DecimalWidget as BaseDecimalWidget,
    BooleanWidget as BaseBooleanWidget,
)


class NaturalKeyForeignKeyWidget(BaseForeignKeyWidget):
    """
    Widget pour résoudre une ForeignKey par un champ naturel au lieu de la PK.

    Permet aux utilisateurs d'utiliser des identifiants lisibles (nom, code,
    référence) dans leurs fichiers d'import au lieu des UUID.

    Exemple d'utilisation:
        mandat = fields.Field(
            column_name='reference_mandat',
            attribute='mandat',
            widget=NaturalKeyForeignKeyWidget(Mandat, field='reference')
        )

    Dans le CSV, l'utilisateur écrit "DUPO-2024-001" au lieu de l'UUID.
    """

    def __init__(
        self,
        model: Type[Model],
        field: str = 'pk',
        create_if_missing: bool = False,
        case_insensitive: bool = False,
        use_natural_key: bool = True,
        **kwargs
    ):
        """
        Args:
            model: Le modèle Django cible
            field: Le champ à utiliser pour la recherche (ex: 'reference', 'code', 'nom')
            create_if_missing: Si True, crée l'objet s'il n'existe pas
            case_insensitive: Si True, la recherche est insensible à la casse
            use_natural_key: Si True, utilise la méthode natural_key() du modèle si disponible
        """
        self.create_if_missing = create_if_missing
        self.case_insensitive = case_insensitive
        self.use_natural_key = use_natural_key
        super().__init__(model, field=field, **kwargs)

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[Model]:
        """
        Résout la valeur en instance du modèle.

        Args:
            value: La valeur du champ dans le fichier d'import
            row: La ligne complète (pour les lookups multi-champs)

        Returns:
            L'instance du modèle ou None

        Raises:
            ValueError: Si l'objet n'est pas trouvé et create_if_missing=False
        """
        if value is None or value == '':
            return None

        value = str(value).strip()

        # Construire le filtre de recherche
        if self.case_insensitive:
            lookup = {f'{self.field}__iexact': value}
        else:
            lookup = {self.field: value}

        try:
            return self.model.objects.get(**lookup)
        except self.model.DoesNotExist:
            if self.create_if_missing:
                return self.model.objects.create(**{self.field: value})
            raise ValueError(
                _("{model} avec {field}='{value}' non trouvé").format(
                    model=self.model._meta.verbose_name,
                    field=self.field,
                    value=value
                )
            )
        except self.model.MultipleObjectsReturned:
            raise ValueError(
                _("Plusieurs {model} trouvés avec {field}='{value}'. "
                  "Veuillez préciser davantage.").format(
                    model=self.model._meta.verbose_name_plural,
                    field=self.field,
                    value=value
                )
            )

    def render(self, value: Optional[Model], obj: Optional[Model] = None) -> str:
        """
        Exporte la valeur en utilisant le champ naturel.

        Args:
            value: L'instance du modèle lié
            obj: L'objet parent (non utilisé)

        Returns:
            La valeur du champ naturel ou chaîne vide
        """
        if value is None:
            return ''

        return str(getattr(value, self.field, ''))


class MandatAwareForeignKeyWidget(NaturalKeyForeignKeyWidget):
    """
    Widget ForeignKey avec validation d'accès au Mandat.

    Vérifie que l'utilisateur a accès au Mandat référencé avant de
    permettre l'import. Utilisé pour tous les champs FK vers Mandat.

    Exemple d'utilisation:
        mandat = fields.Field(
            column_name='reference_mandat',
            attribute='mandat',
            widget=MandatAwareForeignKeyWidget(Mandat, field='reference')
        )
    """

    def __init__(self, model: Type[Model], field: str = 'reference', **kwargs):
        super().__init__(model, field=field, **kwargs)
        self.user = None
        self.accessible_mandats = None

    def set_user(self, user):
        """
        Définit l'utilisateur pour la validation des accès.

        Appelé par la Resource avant l'import.
        """
        self.user = user
        self._load_accessible_mandats()

    def _load_accessible_mandats(self):
        """Charge la liste des mandats accessibles par l'utilisateur."""
        if self.user is None:
            self.accessible_mandats = self.model.objects.none()
            return

        if self.user.is_superuser:
            self.accessible_mandats = self.model.objects.all()
        elif hasattr(self.user, 'is_manager') and self.user.is_manager():
            self.accessible_mandats = self.model.objects.all()
        else:
            # Utilisateur standard: seulement ses mandats
            self.accessible_mandats = self.model.objects.filter(
                Q(responsable=self.user) | Q(equipe=self.user)
            ).distinct()

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[Model]:
        """
        Résout le Mandat et vérifie les droits d'accès.
        """
        mandat = super().clean(value, row, **kwargs)

        if mandat is None:
            return None

        # Vérifier l'accès
        if self.accessible_mandats is not None:
            if not self.accessible_mandats.filter(pk=mandat.pk).exists():
                raise ValueError(
                    _("Vous n'avez pas accès au mandat '{reference}'").format(
                        reference=value
                    )
                )

        return mandat


class MultiFieldLookupWidget(BaseForeignKeyWidget):
    """
    Widget pour rechercher un objet par plusieurs champs.

    Utile quand un seul champ n'est pas suffisant pour identifier
    un objet de manière unique (ex: Contact par email + nom client).

    Exemple d'utilisation:
        contact = fields.Field(
            column_name='contact',
            attribute='contact',
            widget=MultiFieldLookupWidget(
                Contact,
                lookup_fields=['email', 'client__nom'],
                separator='|'
            )
        )

    Dans le CSV: "john@example.com|Dupont SA"
    """

    def __init__(
        self,
        model: Type[Model],
        lookup_fields: List[str],
        separator: str = '|',
        case_insensitive: bool = True,
        **kwargs
    ):
        """
        Args:
            model: Le modèle Django cible
            lookup_fields: Liste des champs pour la recherche (dans l'ordre)
            separator: Séparateur utilisé dans la valeur d'import
            case_insensitive: Si True, recherche insensible à la casse
        """
        self.lookup_fields = lookup_fields
        self.separator = separator
        self.case_insensitive = case_insensitive
        super().__init__(model, field=lookup_fields[0], **kwargs)

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[Model]:
        if value is None or value == '':
            return None

        # Séparer les valeurs
        values = str(value).split(self.separator)

        if len(values) != len(self.lookup_fields):
            raise ValueError(
                _("Format invalide. Attendu: {fields} séparés par '{sep}'").format(
                    fields=' + '.join(self.lookup_fields),
                    sep=self.separator
                )
            )

        # Construire le filtre
        lookup = {}
        for field, val in zip(self.lookup_fields, values):
            val = val.strip()
            if self.case_insensitive:
                lookup[f'{field}__iexact'] = val
            else:
                lookup[field] = val

        try:
            return self.model.objects.get(**lookup)
        except self.model.DoesNotExist:
            raise ValueError(
                _("{model} non trouvé avec {criteria}").format(
                    model=self.model._meta.verbose_name,
                    criteria=', '.join(f"{f}='{v}'" for f, v in zip(self.lookup_fields, values))
                )
            )
        except self.model.MultipleObjectsReturned:
            raise ValueError(
                _("Plusieurs {model} trouvés. Veuillez préciser davantage.").format(
                    model=self.model._meta.verbose_name_plural
                )
            )

    def render(self, value: Optional[Model], obj: Optional[Model] = None) -> str:
        if value is None:
            return ''

        parts = []
        for field in self.lookup_fields:
            # Supporter les champs avec __ (relations)
            current = value
            for part in field.split('__'):
                current = getattr(current, part, None)
                if current is None:
                    break
            parts.append(str(current) if current else '')

        return self.separator.join(parts)


class DateWidget(BaseDateWidget):
    """
    Widget de date avec support de multiples formats.

    Supporte les formats suisses et internationaux:
    - DD.MM.YYYY (format suisse)
    - DD/MM/YYYY (format européen)
    - YYYY-MM-DD (format ISO)
    """

    FORMATS = [
        '%d.%m.%Y',   # Suisse: 31.12.2024
        '%d/%m/%Y',   # Européen: 31/12/2024
        '%Y-%m-%d',   # ISO: 2024-12-31
        '%d-%m-%Y',   # Alternatif: 31-12-2024
    ]

    def __init__(self, formats: Optional[List[str]] = None, **kwargs):
        self.formats = formats or self.FORMATS
        super().__init__(**kwargs)

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[date]:
        if value is None or value == '':
            return None

        # Si c'est déjà une date
        if isinstance(value, date):
            return value

        value = str(value).strip()

        # Essayer les différents formats
        for fmt in self.formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        # Essayer le parser Django
        parsed = parse_date(value)
        if parsed:
            return parsed

        raise ValueError(
            _("Format de date invalide: '{value}'. "
              "Formats acceptés: {formats}").format(
                value=value,
                formats=', '.join(self.formats)
            )
        )

    def render(self, value: Optional[date], obj: Optional[Model] = None) -> str:
        if value is None:
            return ''
        # Export en format suisse par défaut
        return value.strftime('%d.%m.%Y')


class DecimalWidget(BaseDecimalWidget):
    """
    Widget Decimal avec support des formats numériques suisses.

    Gère les séparateurs:
    - Point (.) comme séparateur décimal (international)
    - Virgule (,) comme séparateur décimal (FR/DE)
    - Apostrophe (') comme séparateur de milliers (suisse)
    """

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[Decimal]:
        if value is None or value == '':
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        # Nettoyer la valeur
        value = str(value).strip()

        # Retirer le symbole monétaire
        for symbol in ['CHF', 'EUR', '€', 'Fr.', 'fr.']:
            value = value.replace(symbol, '').strip()

        # Retirer les espaces et apostrophes (séparateurs de milliers)
        value = value.replace("'", '').replace(' ', '').replace('\xa0', '')

        # Gérer la virgule comme séparateur décimal
        # Si on a à la fois point et virgule, la virgule est le séparateur décimal
        if ',' in value and '.' in value:
            # Format européen: 1.234,56
            value = value.replace('.', '').replace(',', '.')
        elif ',' in value:
            # Virgule seule = séparateur décimal
            value = value.replace(',', '.')

        try:
            return Decimal(value)
        except InvalidOperation:
            raise ValueError(
                _("Valeur numérique invalide: '{value}'").format(value=value)
            )

    def render(self, value: Optional[Decimal], obj: Optional[Model] = None) -> str:
        if value is None:
            return ''
        # Export avec 2 décimales
        return str(value.quantize(Decimal('0.01')))


class BooleanWidget(BaseBooleanWidget):
    """
    Widget booléen avec support multilingue.

    Valeurs acceptées pour True:
    - oui, yes, ja, si, sì (multilingue)
    - 1, true, vrai, wahr

    Valeurs acceptées pour False:
    - non, no, nein (multilingue)
    - 0, false, faux, falsch
    """

    TRUE_VALUES = {
        'true', '1', 'oui', 'yes', 'ja', 'si', 'sì',
        'vrai', 'wahr', 'vero', 'o', 'y', 'j', 'x', '✓', '✔'
    }
    FALSE_VALUES = {
        'false', '0', 'non', 'no', 'nein',
        'faux', 'falsch', 'falso', 'n', ''
    }

    def clean(self, value: Any, row: Optional[Dict] = None, **kwargs) -> Optional[bool]:
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        value = str(value).strip().lower()

        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False

        raise ValueError(
            _("Valeur booléenne invalide: '{value}'. "
              "Valeurs acceptées: oui/non, yes/no, 1/0").format(value=value)
        )

    def render(self, value: Optional[bool], obj: Optional[Model] = None) -> str:
        if value is None:
            return ''
        # Export en français par défaut
        return 'Oui' if value else 'Non'
