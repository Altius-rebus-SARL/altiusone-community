# documents/services/digest_service.py
"""
Service de generation de digests periodiques.

Genere des resumes intelligents hebdomadaires, mensuels
ou trimestriels pour chaque mandat actif.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from django.db.models import Count, Sum

logger = logging.getLogger(__name__)


class DigestService:
    """
    Genere des resumes periodiques intelligents pour les mandats.
    """

    def __init__(self):
        self._ai_service = None
        self._temporal_service = None

    @property
    def ai_service(self):
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    @property
    def temporal_service(self):
        if self._temporal_service is None:
            from documents.services.temporal_service import TemporalAnalysisService
            self._temporal_service = TemporalAnalysisService()
        return self._temporal_service

    def generer_digest(
        self,
        mandat_id: str,
        type_digest: str,
        periode_debut: date,
        periode_fin: date
    ) -> Optional['MandatDigest']:
        """
        Genere un digest pour un mandat et une periode.

        Args:
            mandat_id: UUID du mandat
            type_digest: HEBDOMADAIRE, MENSUEL, TRIMESTRIEL
            periode_debut: Debut de la periode
            periode_fin: Fin de la periode

        Returns:
            Instance MandatDigest creee
        """
        from documents.models import Document
        from documents.models_intelligence import MandatInsight, MandatDigest
        from core.models import Mandat, Notification

        mandat = Mandat.objects.select_related('client', 'responsable').get(id=mandat_id)

        # Verifier si un digest existe deja pour cette periode
        existing = MandatDigest.objects.filter(
            mandat=mandat,
            type_digest=type_digest,
            periode_debut=periode_debut
        ).first()
        if existing:
            logger.info(f"Digest deja existant pour {mandat.numero} {type_digest} {periode_debut}")
            return existing

        # Recuperer les documents de la periode
        documents = Document.objects.filter(
            mandat=mandat,
            is_active=True,
            date_upload__date__gte=periode_debut,
            date_upload__date__lte=periode_fin,
        )

        # Recuperer les insights de la periode
        insights = MandatInsight.objects.filter(
            mandat=mandat,
            created_at__date__gte=periode_debut,
            created_at__date__lte=periode_fin,
        )

        # Calculer les statistiques
        doc_stats = documents.aggregate(
            nb_docs=Count('id'),
            taille_totale=Sum('taille'),
        )

        types_repartition = dict(
            documents.values_list('prediction_type').annotate(
                count=Count('id')
            ).values_list('prediction_type', 'count')
        )

        statistiques = {
            'documents_ajoutes': doc_stats['nb_docs'] or 0,
            'taille_totale_mb': round((doc_stats['taille_totale'] or 0) / (1024 * 1024), 1),
            'types_documents': types_repartition,
            'nb_insights': insights.count(),
            'insights_critiques': insights.filter(severite='CRITICAL').count(),
            'insights_warning': insights.filter(severite='WARNING').count(),
        }

        # Generer le resume IA
        resume = ''
        points_cles = []

        if self.ai_service.enabled:
            resume, points_cles = self._generer_resume_ia(
                mandat, type_digest, periode_debut, periode_fin,
                statistiques, insights, documents
            )
        else:
            resume = (
                f"Période {periode_debut.strftime('%d.%m.%Y')} - {periode_fin.strftime('%d.%m.%Y')}: "
                f"{statistiques['documents_ajoutes']} documents ajoutés, "
                f"{statistiques['nb_insights']} insights générés."
            )

        # Creer le digest
        digest = MandatDigest.objects.create(
            mandat=mandat,
            type_digest=type_digest,
            periode_debut=periode_debut,
            periode_fin=periode_fin,
            resume=resume,
            points_cles=points_cles,
            statistiques=statistiques,
        )

        # Lier les insights et documents
        if insights.exists():
            digest.insights_periode.set(insights)
        if documents.exists():
            digest.documents_periode.set(documents[:100])  # Limiter pour perf

        # Notifier le responsable
        Notification.objects.create(
            destinataire=mandat.responsable,
            titre=f"Digest {digest.get_type_digest_display()} - {mandat.numero}",
            message=f"Nouveau résumé disponible pour la période "
                    f"{periode_debut.strftime('%d.%m.%Y')} - {periode_fin.strftime('%d.%m.%Y')}",
            type_notification='INFO',
            mandat=mandat,
            lien_action=f'/documents/mandats/{mandat.id}/digests/',
            lien_texte='Voir le digest',
        )

        logger.info(f"Digest {type_digest} genere pour {mandat.numero}")
        return digest

    def generer_digests_hebdomadaires(self) -> int:
        """
        Genere un digest hebdomadaire pour chaque mandat actif.

        Returns:
            Nombre de digests generes
        """
        from core.models import Mandat

        aujourd_hui = date.today()
        # Semaine ecoulee (lundi a dimanche)
        fin = aujourd_hui - timedelta(days=1)  # Hier
        debut = fin - timedelta(days=6)  # 7 jours avant

        count = 0
        mandats = Mandat.objects.filter(statut='ACTIF')

        for mandat in mandats:
            try:
                digest = self.generer_digest(
                    str(mandat.id), 'HEBDOMADAIRE', debut, fin
                )
                if digest:
                    count += 1
            except Exception as e:
                logger.error(f"Erreur digest hebdo mandat {mandat.numero}: {e}")

        logger.info(f"Digests hebdomadaires: {count} generes")
        return count

    def generer_digests_mensuels(self) -> int:
        """
        Genere un digest mensuel pour chaque mandat actif.

        Returns:
            Nombre de digests generes
        """
        from core.models import Mandat

        aujourd_hui = date.today()
        # Mois ecoule
        fin = aujourd_hui.replace(day=1) - timedelta(days=1)
        debut = fin.replace(day=1)

        count = 0
        mandats = Mandat.objects.filter(statut='ACTIF')

        for mandat in mandats:
            try:
                digest = self.generer_digest(
                    str(mandat.id), 'MENSUEL', debut, fin
                )
                if digest:
                    count += 1
            except Exception as e:
                logger.error(f"Erreur digest mensuel mandat {mandat.numero}: {e}")

        logger.info(f"Digests mensuels: {count} generes")
        return count

    def _generer_resume_ia(
        self, mandat, type_digest, debut, fin,
        statistiques, insights_qs, documents_qs
    ) -> tuple:
        """
        Genere le resume et les points cles via IA.

        Returns:
            Tuple (resume_text, points_cles_list)
        """
        # Construire le contexte pour l'IA
        insights_text = ""
        for insight in insights_qs[:10]:
            insights_text += f"- [{insight.get_severite_display()}] {insight.titre}\n"

        types_text = "\n".join(
            f"- {t or 'Non classé'}: {c}"
            for t, c in statistiques.get('types_documents', {}).items()
        )

        prompt = f"""Genere un resume executif pour le mandat {mandat.numero} ({mandat.client.raison_sociale if mandat.client else 'N/A'}).

Période: {debut.strftime('%d.%m.%Y')} - {fin.strftime('%d.%m.%Y')} ({type_digest})

Statistiques:
- Documents ajoutés: {statistiques['documents_ajoutes']}
- Taille totale: {statistiques['taille_totale_mb']} MB
- Insights: {statistiques['nb_insights']} (dont {statistiques['insights_critiques']} critiques)

Répartition par type:
{types_text}

Alertes et insights:
{insights_text or 'Aucun insight pour cette période.'}

Reponds en JSON:
{{"resume": "Resume executif en 3-5 phrases...", "points_cles": ["Point 1", "Point 2", "Point 3"]}}"""

        try:
            response = self.ai_service.chat(
                message=prompt,
                system="Tu es un assistant fiduciaire suisse. Genere des resumes executifs clairs et professionnels.",
                temperature=0.3,
                max_tokens=600
            )

            import json
            response_text = response.get('response', '')
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                return (
                    result.get('resume', ''),
                    result.get('points_cles', [])
                )
        except Exception as e:
            logger.error(f"Erreur IA generation resume: {e}")

        # Fallback sans IA
        return (
            f"Période {debut.strftime('%d.%m.%Y')} - {fin.strftime('%d.%m.%Y')}: "
            f"{statistiques['documents_ajoutes']} documents ajoutés.",
            []
        )
