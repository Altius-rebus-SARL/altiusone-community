# documents/services/temporal_service.py
"""
Service d'analyse temporelle des donnees d'un mandat.

Analyse l'evolution temporelle: volumes, tendances,
regularite des documents recurrents, anomalies de pattern.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

logger = logging.getLogger(__name__)


class TemporalAnalysisService:
    """
    Analyse l'evolution temporelle des donnees d'un mandat.
    """

    def __init__(self):
        self._ai_service = None

    @property
    def ai_service(self):
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    def analyser_tendances(self, mandat_id: str, periode_mois: int = 12) -> Dict:
        """
        Analyse les tendances documentaires sur une periode.

        Args:
            mandat_id: UUID du mandat
            periode_mois: Nombre de mois a analyser

        Returns:
            Dict avec tendances, previsions, anomalies_temporelles
        """
        from documents.models import Document

        date_debut = date.today() - timedelta(days=periode_mois * 30)

        # Grouper les documents par mois
        docs_par_mois = (
            Document.objects.filter(
                mandat_id=mandat_id,
                is_active=True,
                date_upload__gte=date_debut,
            )
            .annotate(mois=TruncMonth('date_upload'))
            .values('mois')
            .annotate(
                nb_docs=Count('id'),
                taille_totale=Sum('taille'),
            )
            .order_by('mois')
        )

        # Repartition par type et par mois
        types_par_mois = (
            Document.objects.filter(
                mandat_id=mandat_id,
                is_active=True,
                date_upload__gte=date_debut,
            )
            .annotate(mois=TruncMonth('date_upload'))
            .values('mois', 'prediction_type')
            .annotate(count=Count('id'))
            .order_by('mois')
        )

        # Formater les donnees
        mois_data = []
        for entry in docs_par_mois:
            mois_data.append({
                'mois': entry['mois'].strftime('%Y-%m') if entry['mois'] else 'N/A',
                'nb_docs': entry['nb_docs'],
                'taille_mb': round((entry['taille_totale'] or 0) / (1024 * 1024), 1),
            })

        types_data = {}
        for entry in types_par_mois:
            mois_str = entry['mois'].strftime('%Y-%m') if entry['mois'] else 'N/A'
            type_doc = entry['prediction_type'] or 'Non classé'
            if mois_str not in types_data:
                types_data[mois_str] = {}
            types_data[mois_str][type_doc] = entry['count']

        result = {
            'tendances': [],
            'previsions': [],
            'anomalies_temporelles': [],
            'donnees_brutes': {
                'par_mois': mois_data,
                'types_par_mois': types_data,
            }
        }

        # Analyse IA des tendances
        if self.ai_service.enabled and mois_data:
            donnees_text = "\n".join(
                f"- {m['mois']}: {m['nb_docs']} documents, {m['taille_mb']} MB"
                for m in mois_data
            )

            prompt = f"""Analyse l'evolution documentaire de ce mandat sur {periode_mois} mois:

{donnees_text}

Identifie les tendances (hausse/baisse du volume), previsions, et anomalies temporelles.
Reponds en JSON:
{{"tendances": ["tendance1", "tendance2"], "previsions": ["prevision1"], "anomalies": ["anomalie1"]}}"""

            try:
                response = self.ai_service.chat(
                    message=prompt,
                    system="Tu es un analyste de donnees. Identifie les tendances et anomalies.",
                    temperature=0.3,
                    max_tokens=600
                )

                import json
                response_text = response.get('response', '')
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    ai_result = json.loads(response_text[json_start:json_end])
                    result['tendances'] = ai_result.get('tendances', [])
                    result['previsions'] = ai_result.get('previsions', [])
                    result['anomalies_temporelles'] = ai_result.get('anomalies', [])
            except Exception as e:
                logger.error(f"Erreur IA analyse tendances: {e}")

        return result

    def comparer_periodes(
        self, mandat_id: str, periode1: tuple, periode2: tuple
    ) -> Dict:
        """
        Compare deux periodes d'un mandat.

        Args:
            mandat_id: UUID du mandat
            periode1: (date_debut, date_fin) premiere periode
            periode2: (date_debut, date_fin) deuxieme periode

        Returns:
            Dict avec comparaison volumes, types, resume IA
        """
        from documents.models import Document

        def get_stats(debut, fin):
            docs = Document.objects.filter(
                mandat_id=mandat_id,
                is_active=True,
                date_upload__gte=debut,
                date_upload__lte=fin,
            )
            types = docs.values('prediction_type').annotate(
                count=Count('id')
            ).order_by('-count')
            return {
                'nb_docs': docs.count(),
                'taille_totale': docs.aggregate(t=Sum('taille'))['t'] or 0,
                'types': {t['prediction_type'] or 'N/A': t['count'] for t in types},
            }

        stats1 = get_stats(*periode1)
        stats2 = get_stats(*periode2)

        result = {
            'periode1': {
                'debut': str(periode1[0]),
                'fin': str(periode1[1]),
                **stats1,
            },
            'periode2': {
                'debut': str(periode2[0]),
                'fin': str(periode2[1]),
                **stats2,
            },
            'differences': {
                'docs_delta': stats2['nb_docs'] - stats1['nb_docs'],
                'taille_delta': stats2['taille_totale'] - stats1['taille_totale'],
            },
            'resume': '',
        }

        # Resume IA
        if self.ai_service.enabled:
            prompt = f"""Compare ces 2 periodes documentaires:

Période 1 ({periode1[0]} à {periode1[1]}): {stats1['nb_docs']} docs, types: {stats1['types']}
Période 2 ({periode2[0]} à {periode2[1]}): {stats2['nb_docs']} docs, types: {stats2['types']}

Resume les differences notables en 2-3 phrases."""

            try:
                response = self.ai_service.chat(
                    message=prompt,
                    system="Tu es un analyste de donnees. Resume les differences entre periodes.",
                    temperature=0.3,
                    max_tokens=300
                )
                result['resume'] = response.get('response', '')
            except Exception as e:
                logger.error(f"Erreur IA comparaison periodes: {e}")

        return result

    def detecter_anomalies_temporelles(self, mandat_id: str) -> List:
        """
        Detecte les ruptures de pattern dans les documents recurrents.

        Args:
            mandat_id: UUID du mandat

        Returns:
            Liste de MandatInsight de type TENDANCE ou ALERTE
        """
        from documents.models import Document
        from documents.models_intelligence import MandatInsight
        from core.models import Mandat

        mandat = Mandat.objects.get(id=mandat_id)
        insights = []

        # Analyser les 12 derniers mois
        date_debut = date.today() - timedelta(days=365)

        # Compter les documents par mois
        docs_par_mois = (
            Document.objects.filter(
                mandat_id=mandat_id,
                is_active=True,
                date_upload__gte=date_debut,
            )
            .annotate(mois=TruncMonth('date_upload'))
            .values('mois')
            .annotate(nb=Count('id'))
            .order_by('mois')
        )

        mois_counts = [entry['nb'] for entry in docs_par_mois]

        if len(mois_counts) < 3:
            return insights

        # Detecter mois sans document (gap)
        mois_list = [entry['mois'] for entry in docs_par_mois]
        if mois_list:
            current = mois_list[0]
            mois_manquants = []
            while current <= date.today().replace(day=1):
                if current not in mois_list:
                    mois_manquants.append(current.strftime('%Y-%m'))
                # Avancer au mois suivant
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            if mois_manquants:
                insight = MandatInsight.objects.create(
                    mandat=mandat,
                    type_insight='TENDANCE',
                    severite='WARNING' if len(mois_manquants) >= 2 else 'INFO',
                    titre=f"{len(mois_manquants)} mois sans document",
                    description=(
                        f"Aucun document reçu pour les mois suivants: "
                        f"{', '.join(mois_manquants[:6])}"
                        + (f" et {len(mois_manquants) - 6} autres" if len(mois_manquants) > 6 else "")
                    ),
                    donnees={
                        'mois_manquants': mois_manquants,
                        'mois_avec_docs': [m.strftime('%Y-%m') for m in mois_list],
                    }
                )
                insights.append(insight)

        # Detecter pic anormal (> 2x la moyenne)
        if mois_counts:
            moyenne = sum(mois_counts) / len(mois_counts)
            if moyenne > 0:
                for entry in docs_par_mois:
                    if entry['nb'] > moyenne * 2.5:
                        mois_str = entry['mois'].strftime('%Y-%m')
                        insight = MandatInsight.objects.create(
                            mandat=mandat,
                            type_insight='ALERTE',
                            severite='INFO',
                            titre=f"Pic de documents en {mois_str}",
                            description=(
                                f"{entry['nb']} documents reçus en {mois_str} "
                                f"(moyenne: {moyenne:.0f}/mois). "
                                f"Ce volume est anormalement élevé."
                            ),
                            donnees={
                                'mois': mois_str,
                                'nb_docs': entry['nb'],
                                'moyenne': round(moyenne, 1),
                            }
                        )
                        insights.append(insight)

        return insights
