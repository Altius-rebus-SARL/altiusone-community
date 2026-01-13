# analytics/services/rapport_section_service.py
"""
Service pour la gestion des sections de rapport.

Gère la création, modification, réorganisation et suppression des sections.
"""

import logging
from typing import Optional
from django.db import transaction
from django.db.models import QuerySet

from analytics.models import (
    Rapport,
    SectionRapport,
    TypeGraphiqueRapport,
    ModeleRapport,
)

logger = logging.getLogger(__name__)


class RapportSectionService:
    """Service pour gérer les sections de rapport."""

    # Espacement par défaut entre les ordres (permet l'insertion)
    ORDRE_ESPACEMENT = 10

    @classmethod
    def get_sections_rapport(cls, rapport: Rapport) -> QuerySet[SectionRapport]:
        """
        Récupère toutes les sections d'un rapport ordonnées.

        Args:
            rapport: Le rapport concerné

        Returns:
            QuerySet des sections ordonnées
        """
        return rapport.sections.filter(is_active=True).order_by('ordre')

    @classmethod
    def get_graphiques_compatibles(cls, type_rapport: str) -> QuerySet[TypeGraphiqueRapport]:
        """
        Récupère les graphiques prédéfinis compatibles avec un type de rapport.

        Args:
            type_rapport: Le type de rapport (BILAN, COMPTE_RESULTATS, etc.)

        Returns:
            QuerySet des graphiques compatibles
        """
        return TypeGraphiqueRapport.objects.filter(
            actif=True,
            types_rapport_compatibles__contains=[type_rapport]
        ).order_by('ordre')

    @classmethod
    @transaction.atomic
    def creer_section(
        cls,
        rapport: Rapport,
        type_section: str,
        contenu_texte: str = '',
        type_graphique: Optional[TypeGraphiqueRapport] = None,
        config: Optional[dict] = None,
        position: Optional[int] = None,
    ) -> SectionRapport:
        """
        Crée une nouvelle section pour un rapport.

        Args:
            rapport: Le rapport parent
            type_section: Type de section (titre, texte, graphique, etc.)
            contenu_texte: Contenu HTML pour les sections texte/titre
            type_graphique: Graphique prédéfini pour les sections graphique
            config: Configuration JSON additionnelle
            position: Position souhaitée (None = à la fin)

        Returns:
            La section créée
        """
        # Calculer l'ordre
        if position is not None:
            ordre = position * cls.ORDRE_ESPACEMENT
        else:
            # Ajouter à la fin
            last_section = rapport.sections.order_by('-ordre').first()
            ordre = (last_section.ordre + cls.ORDRE_ESPACEMENT) if last_section else 0

        section = SectionRapport.objects.create(
            rapport=rapport,
            type_section=type_section,
            contenu_texte=contenu_texte,
            type_graphique=type_graphique,
            config=config or {},
            ordre=ordre,
            visible=True,
        )

        logger.info(f"Section {type_section} créée pour rapport {rapport.id}")
        return section

    @classmethod
    @transaction.atomic
    def modifier_section(
        cls,
        section: SectionRapport,
        contenu_texte: Optional[str] = None,
        type_graphique: Optional[TypeGraphiqueRapport] = None,
        config: Optional[dict] = None,
        visible: Optional[bool] = None,
    ) -> SectionRapport:
        """
        Modifie une section existante.

        Args:
            section: La section à modifier
            contenu_texte: Nouveau contenu texte (si fourni)
            type_graphique: Nouveau graphique (si fourni)
            config: Nouvelle configuration (si fournie)
            visible: Nouvelle visibilité (si fournie)

        Returns:
            La section modifiée
        """
        if contenu_texte is not None:
            section.contenu_texte = contenu_texte

        if type_graphique is not None:
            section.type_graphique = type_graphique

        if config is not None:
            section.config = config

        if visible is not None:
            section.visible = visible

        section.save()
        logger.info(f"Section {section.id} modifiée")
        return section

    @classmethod
    @transaction.atomic
    def supprimer_section(cls, section: SectionRapport) -> bool:
        """
        Supprime une section (soft delete).

        Args:
            section: La section à supprimer

        Returns:
            True si supprimée avec succès
        """
        section.is_active = False
        section.save(update_fields=['is_active'])
        logger.info(f"Section {section.id} supprimée")
        return True

    @classmethod
    @transaction.atomic
    def reordonner_sections(cls, rapport: Rapport, ordre_ids: list[str]) -> bool:
        """
        Réordonne les sections selon la liste d'IDs fournie.

        Args:
            rapport: Le rapport concerné
            ordre_ids: Liste des IDs de section dans l'ordre souhaité

        Returns:
            True si réordonnées avec succès
        """
        for index, section_id in enumerate(ordre_ids):
            SectionRapport.objects.filter(
                id=section_id,
                rapport=rapport
            ).update(ordre=index * cls.ORDRE_ESPACEMENT)

        logger.info(f"Sections du rapport {rapport.id} réordonnées")
        return True

    @classmethod
    @transaction.atomic
    def dupliquer_section(cls, section: SectionRapport) -> SectionRapport:
        """
        Duplique une section.

        Args:
            section: La section à dupliquer

        Returns:
            La nouvelle section dupliquée
        """
        # Trouver la position juste après
        nouvelle_section = SectionRapport.objects.create(
            rapport=section.rapport,
            type_section=section.type_section,
            contenu_texte=section.contenu_texte,
            type_graphique=section.type_graphique,
            config=section.config.copy() if section.config else {},
            ordre=section.ordre + 1,  # Juste après
            visible=section.visible,
        )

        # Réajuster les ordres
        cls._normaliser_ordres(section.rapport)

        logger.info(f"Section {section.id} dupliquée vers {nouvelle_section.id}")
        return nouvelle_section

    @classmethod
    @transaction.atomic
    def initialiser_sections_depuis_modele(
        cls,
        rapport: Rapport,
        modele: Optional[ModeleRapport] = None
    ) -> list[SectionRapport]:
        """
        Initialise les sections d'un rapport à partir d'un modèle.

        Si aucun modèle n'est fourni, utilise le modèle par défaut du type de rapport.

        Args:
            rapport: Le rapport à initialiser
            modele: Le modèle à utiliser (optionnel)

        Returns:
            Liste des sections créées
        """
        # Supprimer les sections existantes
        rapport.sections.all().delete()

        # Trouver le modèle
        if modele is None:
            modele = ModeleRapport.objects.filter(
                type_rapport=rapport.type_rapport,
                actif=True,
                proprietaire__isnull=True  # Modèle système
            ).first()

        if modele is None:
            # Créer des sections par défaut basiques
            return cls._creer_sections_defaut_basiques(rapport)

        # Utiliser le modèle pour créer les sections
        return modele.creer_sections_pour_rapport(rapport)

    @classmethod
    def _creer_sections_defaut_basiques(cls, rapport: Rapport) -> list[SectionRapport]:
        """
        Crée des sections par défaut basiques si aucun modèle n'existe.

        Args:
            rapport: Le rapport concerné

        Returns:
            Liste des sections créées
        """
        sections = []

        # Titre
        sections.append(SectionRapport.objects.create(
            rapport=rapport,
            type_section='titre',
            contenu_texte=f'<h1>{rapport.get_type_rapport_display()}</h1>',
            ordre=0,
        ))

        # Texte d'introduction
        sections.append(SectionRapport.objects.create(
            rapport=rapport,
            type_section='texte',
            contenu_texte='<p>Rapport généré automatiquement.</p>',
            ordre=10,
        ))

        # Tableau principal
        sections.append(SectionRapport.objects.create(
            rapport=rapport,
            type_section='tableau',
            config={'source': 'auto'},
            ordre=20,
        ))

        logger.info(f"Sections par défaut créées pour rapport {rapport.id}")
        return sections

    @classmethod
    def _normaliser_ordres(cls, rapport: Rapport) -> None:
        """
        Normalise les ordres des sections (espace régulier).

        Args:
            rapport: Le rapport concerné
        """
        sections = list(rapport.sections.filter(is_active=True).order_by('ordre'))
        for index, section in enumerate(sections):
            nouveau_ordre = index * cls.ORDRE_ESPACEMENT
            if section.ordre != nouveau_ordre:
                section.ordre = nouveau_ordre
                section.save(update_fields=['ordre'])

    @classmethod
    def formater_contenu_avec_variables(
        cls,
        contenu: str,
        rapport: Rapport
    ) -> str:
        """
        Remplace les variables dans le contenu par leurs valeurs.

        Variables supportées:
        - {date_debut}, {date_fin}
        - {mandat_nom}
        - {type_rapport}

        Args:
            contenu: Le contenu avec variables
            rapport: Le rapport pour les valeurs

        Returns:
            Contenu avec variables remplacées
        """
        variables = {
            'date_debut': rapport.date_debut.strftime('%d.%m.%Y') if rapport.date_debut else '',
            'date_fin': rapport.date_fin.strftime('%d.%m.%Y') if rapport.date_fin else '',
            'mandat_nom': rapport.mandat.client.raison_sociale if rapport.mandat else '',
            'type_rapport': rapport.get_type_rapport_display(),
        }

        for var, valeur in variables.items():
            contenu = contenu.replace('{' + var + '}', str(valeur))

        return contenu
