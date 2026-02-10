# documents/services/insight_service.py
"""
Service de generation d'insights proactifs.

Analyse un mandat pour detecter anomalies, documents manquants,
incoherences et generer des recommandations.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


# Documents attendus par type de mandat
DOCUMENTS_ATTENDUS = {
    'COMPTA': [
        ('RELEVE_BANQUE', 'Relevés bancaires'),
        ('FACTURE_ACHAT', 'Factures fournisseurs'),
        ('FACTURE_VENTE', 'Factures clients'),
    ],
    'TVA': [
        ('DECLARATION_TVA', 'Déclaration TVA'),
        ('FACTURE_ACHAT', 'Factures fournisseurs'),
        ('FACTURE_VENTE', 'Factures clients'),
    ],
    'SALAIRES': [
        ('FICHE_SALAIRE', 'Fiches de salaire'),
        ('CERTIFICAT_SALAIRE', 'Certificats de salaire'),
        ('CONTRAT_TRAVAIL', 'Contrats de travail'),
    ],
    'FISCAL': [
        ('DECLARATION_TVA', 'Déclaration TVA'),
        ('ATTESTATION', 'Attestations fiscales'),
    ],
    'GLOBAL': [
        ('RELEVE_BANQUE', 'Relevés bancaires'),
        ('FACTURE_ACHAT', 'Factures fournisseurs'),
        ('FACTURE_VENTE', 'Factures clients'),
        ('DECLARATION_TVA', 'Déclaration TVA'),
        ('FICHE_SALAIRE', 'Fiches de salaire'),
    ],
}


class InsightService:
    """
    Genere des insights proactifs sur un mandat.
    """

    def __init__(self):
        self._ai_service = None

    @property
    def ai_service(self):
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    def analyser_mandat(self, mandat_id: str) -> list:
        """
        Analyse complete d'un mandat.
        Orchestre les sous-analyses:
        1. Detection anomalies montants
        2. Detection documents manquants
        3. Analyse coherence

        Args:
            mandat_id: UUID du mandat

        Returns:
            Liste de MandatInsight crees
        """
        from core.models import Mandat, Notification

        mandat = Mandat.objects.select_related('client', 'responsable').get(id=mandat_id)
        insights = []

        logger.info(f"Debut analyse mandat {mandat.numero}")

        # 1. Anomalies montants
        try:
            insights.extend(self._detecter_anomalies_montants(mandat))
        except Exception as e:
            logger.error(f"Erreur detection anomalies montants: {e}")

        # 2. Documents manquants
        try:
            insights.extend(self._detecter_documents_manquants(mandat))
        except Exception as e:
            logger.error(f"Erreur detection documents manquants: {e}")

        # 3. Coherence
        try:
            insights.extend(self._analyser_coherence(mandat))
        except Exception as e:
            logger.error(f"Erreur analyse coherence: {e}")

        # Creer notifications pour les insights critiques
        for insight in insights:
            if insight.severite == 'CRITICAL':
                Notification.objects.create(
                    destinataire=mandat.responsable,
                    titre=f"[IA] {insight.titre}",
                    message=insight.description[:500],
                    type_notification='WARNING',
                    mandat=mandat,
                    lien_action=f'/documents/mandats/{mandat.id}/insights/',
                    lien_texte='Voir les insights',
                )

        logger.info(f"Mandat {mandat.numero}: {len(insights)} insights generes")
        return insights

    def _detecter_anomalies_montants(self, mandat) -> list:
        """
        Detecte les anomalies de montants dans les documents du mandat.
        """
        from documents.models import Document
        from documents.models_intelligence import MandatInsight

        insights = []

        # Recuperer les montants des metadonnees extraites
        documents = Document.objects.filter(
            mandat=mandat,
            is_active=True,
            metadata_extraite__isnull=False
        ).exclude(metadata_extraite={})

        montants = []
        for doc in documents:
            meta = doc.metadata_extraite
            for key in ('montant', 'montant_total', 'montant_ttc', 'total', 'montant_ht'):
                if key in meta and meta[key]:
                    try:
                        val = str(meta[key]).replace("'", "").replace("CHF", "").strip()
                        montants.append({
                            'document': doc.nom_fichier,
                            'document_id': str(doc.id),
                            'montant': float(val),
                            'champ': key,
                        })
                    except (ValueError, TypeError):
                        pass

        if len(montants) < 3:
            return insights

        # Utiliser l'IA pour detecter des anomalies
        if not self.ai_service.enabled:
            return insights

        montants_text = "\n".join(
            f"- {m['document']}: {m['montant']:.2f} CHF ({m['champ']})"
            for m in montants[:30]
        )

        prompt = f"""Analyse ces montants extraits des documents du mandat {mandat.numero} et detecte les anomalies:

{montants_text}

Detecte: doublons de montants, ecarts inhabituels, montants suspects.
Reponds en JSON:
{{"anomalies": [{{"titre": "...", "description": "...", "severite": "WARNING|CRITICAL", "documents": ["nom1", "nom2"]}}]}}
Si aucune anomalie, reponds: {{"anomalies": []}}"""

        try:
            response = self.ai_service.chat(
                message=prompt,
                system="Tu es un expert-comptable suisse. Analyse les montants et detecte les anomalies.",
                temperature=0.2,
                max_tokens=800
            )

            import json
            response_text = response.get('response', '')
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])

                for anomalie in result.get('anomalies', []):
                    insight = MandatInsight.objects.create(
                        mandat=mandat,
                        type_insight='ANOMALIE',
                        severite=anomalie.get('severite', 'WARNING'),
                        titre=anomalie.get('titre', 'Anomalie de montant détectée'),
                        description=anomalie.get('description', ''),
                        donnees={
                            'montants': montants[:20],
                            'documents_concernes': anomalie.get('documents', []),
                        }
                    )
                    # Lier les documents concernes
                    doc_names = anomalie.get('documents', [])
                    if doc_names:
                        from documents.models import Document
                        docs = Document.objects.filter(
                            mandat=mandat,
                            nom_fichier__in=doc_names
                        )
                        insight.documents.set(docs)
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Erreur IA detection anomalies: {e}")

        return insights

    def _detecter_documents_manquants(self, mandat) -> list:
        """
        Detecte les documents attendus mais absents selon le type de mandat.
        """
        from documents.models import Document
        from documents.models_intelligence import MandatInsight

        insights = []
        type_mandat = mandat.type_mandat or ''
        docs_attendus = DOCUMENTS_ATTENDUS.get(type_mandat, [])

        if not docs_attendus:
            return insights

        # Recuperer les types de documents presents
        types_presents = set(
            Document.objects.filter(
                mandat=mandat,
                is_active=True,
            ).exclude(
                prediction_type=''
            ).values_list('prediction_type', flat=True).distinct()
        )

        manquants = []
        for type_code, type_label in docs_attendus:
            if type_code not in types_presents:
                manquants.append((type_code, type_label))

        if manquants:
            manquants_text = "\n".join(f"- {label} ({code})" for code, label in manquants)
            insight = MandatInsight.objects.create(
                mandat=mandat,
                type_insight='MANQUANT',
                severite='WARNING' if len(manquants) >= 2 else 'INFO',
                titre=f"{len(manquants)} type(s) de document(s) manquant(s)",
                description=(
                    f"Pour un mandat de type {mandat.get_type_mandat_display()}, "
                    f"les documents suivants sont attendus mais absents:\n{manquants_text}"
                ),
                donnees={
                    'type_mandat': type_mandat,
                    'manquants': [{'code': c, 'label': l} for c, l in manquants],
                    'presents': list(types_presents),
                }
            )
            insights.append(insight)

        return insights

    def _analyser_coherence(self, mandat) -> list:
        """
        Analyse la coherence globale des documents du mandat via IA.
        """
        from documents.models import Document
        from documents.models_intelligence import MandatInsight
        from django.db.models import Count

        insights = []

        if not self.ai_service.enabled:
            return insights

        # Construire un resume du dossier
        stats = Document.objects.filter(
            mandat=mandat, is_active=True
        ).values('prediction_type').annotate(
            count=Count('id')
        ).order_by('-count')

        if not stats:
            return insights

        resume = f"Mandat: {mandat.numero} ({mandat.get_type_mandat_display()})\n"
        resume += f"Client: {mandat.client.raison_sociale if mandat.client else 'N/A'}\n"
        resume += f"Période: {mandat.date_debut} - {mandat.date_fin or 'en cours'}\n\n"
        resume += "Documents par type:\n"
        for s in stats:
            resume += f"- {s['prediction_type'] or 'Non classé'}: {s['count']} documents\n"

        prompt = f"""Analyse la coherence de ce dossier client et fais des recommandations:

{resume}

Reponds en JSON:
{{"recommandations": [{{"titre": "...", "description": "...", "severite": "INFO|WARNING"}}]}}
Si tout est coherent, reponds: {{"recommandations": []}}"""

        try:
            response = self.ai_service.chat(
                message=prompt,
                system="Tu es un expert fiduciaire suisse. Analyse la coherence des dossiers clients.",
                temperature=0.3,
                max_tokens=800
            )

            import json
            response_text = response.get('response', '')
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])

                for reco in result.get('recommandations', []):
                    insight = MandatInsight.objects.create(
                        mandat=mandat,
                        type_insight='RECOMMANDATION',
                        severite=reco.get('severite', 'INFO'),
                        titre=reco.get('titre', 'Recommandation'),
                        description=reco.get('description', ''),
                        donnees={'source': 'coherence_analysis'}
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Erreur IA analyse coherence: {e}")

        return insights
