# analytics/insights.py
"""
Service d'analyse intelligente et génération d'insights.

Utilise les données de l'application pour générer des insights,
alertes et recommandations automatiques.
"""
import logging
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from django.db.models import Sum, Avg, Count, Q, F, StdDev
from django.db.models.functions import TruncMonth, TruncWeek
from django.apps import apps

logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types d'insights."""
    ALERT = 'alert'  # Problème urgent
    WARNING = 'warning'  # Attention requise
    INFO = 'info'  # Information
    SUCCESS = 'success'  # Bonne nouvelle
    RECOMMENDATION = 'recommendation'  # Suggestion d'action


class InsightCategory(Enum):
    """Catégories d'insights."""
    FINANCE = 'finance'
    CLIENTS = 'clients'
    FACTURATION = 'facturation'
    TRESORERIE = 'tresorerie'
    SALAIRES = 'salaires'
    DOCUMENTS = 'documents'
    TENDANCE = 'tendance'


@dataclass
class Insight:
    """Un insight généré par le système."""
    type: InsightType
    category: InsightCategory
    title: str
    message: str
    value: Any = None
    reference_value: Any = None
    change_percent: float = None
    priority: int = 50  # 0-100, plus élevé = plus urgent
    action_url: str = None
    action_label: str = None
    metadata: Dict = field(default_factory=dict)


class InsightsEngine:
    """
    Moteur de génération d'insights.

    Analyse les données et génère des insights pertinents.
    """

    def __init__(self, mandat=None):
        self.mandat = mandat
        self.today = date.today()

    def generate_all_insights(self) -> List[Insight]:
        """Génère tous les insights disponibles."""
        insights = []

        # Insights financiers
        insights.extend(self._insights_factures_impayees())
        insights.extend(self._insights_tendance_ca())
        insights.extend(self._insights_delai_paiement())

        # Insights clients
        insights.extend(self._insights_clients_inactifs())
        insights.extend(self._insights_concentration_clients())

        # Insights trésorerie
        insights.extend(self._insights_tresorerie())

        # Insights documents
        insights.extend(self._insights_documents())

        # Insights salaires
        insights.extend(self._insights_salaires())

        # Trier par priorité
        insights.sort(key=lambda x: x.priority, reverse=True)

        return insights

    def _insights_factures_impayees(self) -> List[Insight]:
        """Analyse les factures impayées et en retard."""
        insights = []

        Facture = apps.get_model('facturation', 'Facture')

        # Factures de base
        base_qs = Facture.objects.filter(is_active=True)
        if self.mandat:
            base_qs = base_qs.filter(mandat=self.mandat)

        # Factures en retard
        retard = base_qs.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE'],
            date_echeance__lt=self.today
        ).aggregate(
            count=Count('id'),
            total=Sum('montant_restant')
        )

        if retard['count'] and retard['count'] > 0:
            jours_retard = base_qs.filter(
                statut__in=['EMISE', 'ENVOYEE', 'RELANCEE'],
                date_echeance__lt=self.today
            ).aggregate(
                avg_jours=Avg(F('date_echeance') - self.today)
            )

            priority = min(90, 50 + retard['count'] * 5)

            insights.append(Insight(
                type=InsightType.ALERT if retard['count'] > 5 else InsightType.WARNING,
                category=InsightCategory.FACTURATION,
                title=f"{retard['count']} facture(s) en retard",
                message=f"Montant total impayé: CHF {retard['total'] or 0:,.2f}. "
                        f"Action recommandée: relancer les clients.",
                value=retard['total'],
                priority=priority,
                action_url='/facturation/factures/?statut=EN_RETARD',
                action_label='Voir les factures',
                metadata={
                    'count': retard['count'],
                    'total': float(retard['total'] or 0)
                }
            ))

        # Factures qui vont bientôt expirer
        prochaine_semaine = self.today + timedelta(days=7)
        bientot = base_qs.filter(
            statut__in=['EMISE', 'ENVOYEE'],
            date_echeance__gte=self.today,
            date_echeance__lte=prochaine_semaine
        ).aggregate(count=Count('id'), total=Sum('montant_restant'))

        if bientot['count'] and bientot['count'] > 0:
            insights.append(Insight(
                type=InsightType.INFO,
                category=InsightCategory.FACTURATION,
                title=f"{bientot['count']} facture(s) échéance cette semaine",
                message=f"CHF {bientot['total'] or 0:,.2f} arrivent à échéance dans les 7 jours.",
                value=bientot['total'],
                priority=40,
                metadata={'count': bientot['count']}
            ))

        return insights

    def _insights_tendance_ca(self) -> List[Insight]:
        """Analyse la tendance du chiffre d'affaires."""
        insights = []

        Facture = apps.get_model('facturation', 'Facture')

        # CA des 3 derniers mois vs 3 mois précédents
        trois_mois = self.today - timedelta(days=90)
        six_mois = self.today - timedelta(days=180)

        base_qs = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
            is_active=True
        )
        if self.mandat:
            base_qs = base_qs.filter(mandat=self.mandat)

        # CA récent
        ca_recent = base_qs.filter(
            date_emission__gte=trois_mois
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        # CA période précédente
        ca_precedent = base_qs.filter(
            date_emission__gte=six_mois,
            date_emission__lt=trois_mois
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        if ca_precedent > 0:
            variation = ((ca_recent - ca_precedent) / ca_precedent) * 100

            if variation > 10:
                insights.append(Insight(
                    type=InsightType.SUCCESS,
                    category=InsightCategory.TENDANCE,
                    title="CA en hausse",
                    message=f"Le chiffre d'affaires a augmenté de {variation:.1f}% "
                            f"sur les 3 derniers mois.",
                    value=float(ca_recent),
                    reference_value=float(ca_precedent),
                    change_percent=float(variation),
                    priority=30,
                ))
            elif variation < -10:
                insights.append(Insight(
                    type=InsightType.WARNING,
                    category=InsightCategory.TENDANCE,
                    title="CA en baisse",
                    message=f"Le chiffre d'affaires a diminué de {abs(variation):.1f}% "
                            f"sur les 3 derniers mois. Analyse recommandée.",
                    value=float(ca_recent),
                    reference_value=float(ca_precedent),
                    change_percent=float(variation),
                    priority=60,
                    action_url='/analytics/',
                    action_label='Voir l\'analyse'
                ))

        return insights

    def _insights_delai_paiement(self) -> List[Insight]:
        """Analyse les délais de paiement moyens."""
        insights = []

        Paiement = apps.get_model('facturation', 'Paiement')

        # Délai moyen sur les 6 derniers mois
        six_mois = self.today - timedelta(days=180)

        base_qs = Paiement.objects.filter(
            date_paiement__gte=six_mois,
            valide=True
        )
        if self.mandat:
            base_qs = base_qs.filter(facture__mandat=self.mandat)

        # Calcul manuel du délai moyen
        paiements = base_qs.select_related('facture').all()
        delais = []
        for p in paiements:
            if p.facture.date_emission:
                delai = (p.date_paiement - p.facture.date_emission).days
                if delai >= 0:
                    delais.append(delai)

        if delais:
            delai_moyen = sum(delais) / len(delais)

            if delai_moyen > 45:
                insights.append(Insight(
                    type=InsightType.WARNING,
                    category=InsightCategory.TRESORERIE,
                    title="Délai de paiement élevé",
                    message=f"Le délai de paiement moyen est de {delai_moyen:.0f} jours. "
                            f"Envisagez des conditions de paiement plus strictes.",
                    value=delai_moyen,
                    priority=50,
                ))
            elif delai_moyen < 20:
                insights.append(Insight(
                    type=InsightType.SUCCESS,
                    category=InsightCategory.TRESORERIE,
                    title="Excellents délais de paiement",
                    message=f"Le délai de paiement moyen est de {delai_moyen:.0f} jours. "
                            f"Vos clients paient rapidement!",
                    value=delai_moyen,
                    priority=20,
                ))

        return insights

    def _insights_clients_inactifs(self) -> List[Insight]:
        """Identifie les clients inactifs."""
        insights = []

        Client = apps.get_model('core', 'Client')
        Facture = apps.get_model('facturation', 'Facture')

        # Clients sans facture depuis 6 mois
        six_mois = self.today - timedelta(days=180)

        # Clients qui ont eu des factures avant
        clients_actifs_avant = Facture.objects.filter(
            date_emission__lt=six_mois
        ).values_list('client_id', flat=True).distinct()

        # Clients avec factures récentes
        clients_actifs_recents = Facture.objects.filter(
            date_emission__gte=six_mois
        ).values_list('client_id', flat=True).distinct()

        # Clients devenus inactifs
        clients_inactifs = set(clients_actifs_avant) - set(clients_actifs_recents)

        if len(clients_inactifs) > 0:
            insights.append(Insight(
                type=InsightType.INFO,
                category=InsightCategory.CLIENTS,
                title=f"{len(clients_inactifs)} client(s) inactif(s)",
                message="Ces clients n'ont pas reçu de facture depuis 6 mois. "
                        "Opportunité de relance commerciale.",
                value=len(clients_inactifs),
                priority=35,
                action_url='/core/clients/?inactif=true',
                action_label='Voir les clients'
            ))

        return insights

    def _insights_concentration_clients(self) -> List[Insight]:
        """Analyse la concentration du CA par client."""
        insights = []

        Facture = apps.get_model('facturation', 'Facture')

        # CA par client sur l'année
        un_an = self.today - timedelta(days=365)

        ca_par_client = Facture.objects.filter(
            date_emission__gte=un_an,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).values('client').annotate(
            total=Sum('montant_ht')
        ).order_by('-total')

        if ca_par_client:
            ca_total = sum(c['total'] or 0 for c in ca_par_client)

            if ca_total > 0:
                # Top client
                top_client = ca_par_client[0]
                concentration = (top_client['total'] / ca_total) * 100

                if concentration > 40:
                    insights.append(Insight(
                        type=InsightType.WARNING,
                        category=InsightCategory.CLIENTS,
                        title="Concentration client élevée",
                        message=f"Un seul client représente {concentration:.1f}% du CA. "
                                f"Risque de dépendance. Diversifiez votre portefeuille.",
                        value=float(concentration),
                        priority=55,
                    ))

        return insights

    def _insights_tresorerie(self) -> List[Insight]:
        """Analyse la trésorerie."""
        insights = []

        # Cette analyse nécessite les comptes bancaires
        # Implémentation basique basée sur les factures
        Facture = apps.get_model('facturation', 'Facture')

        base_qs = Facture.objects.filter(is_active=True)
        if self.mandat:
            base_qs = base_qs.filter(mandat=self.mandat)

        # Encours clients (à recevoir)
        encours = base_qs.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE', 'PARTIELLEMENT_PAYEE']
        ).aggregate(total=Sum('montant_restant'))['total'] or Decimal('0')

        if encours > 50000:
            insights.append(Insight(
                type=InsightType.INFO,
                category=InsightCategory.TRESORERIE,
                title="Encours clients important",
                message=f"CHF {encours:,.2f} en attente de paiement. "
                        f"Suivez de près les échéances.",
                value=float(encours),
                priority=45,
            ))

        return insights

    def _insights_documents(self) -> List[Insight]:
        """Analyse les documents non traités."""
        insights = []

        try:
            Document = apps.get_model('documents', 'Document')

            base_qs = Document.objects.filter(is_active=True)
            if self.mandat:
                base_qs = base_qs.filter(mandat=self.mandat)

            # Documents en attente de validation
            en_attente = base_qs.filter(statut_validation='EN_ATTENTE').count()

            if en_attente > 10:
                insights.append(Insight(
                    type=InsightType.INFO,
                    category=InsightCategory.DOCUMENTS,
                    title=f"{en_attente} documents à valider",
                    message="Des documents sont en attente de validation. "
                            "Traitez-les pour maintenir votre GED à jour.",
                    value=en_attente,
                    priority=30,
                    action_url='/documents/?statut=EN_ATTENTE',
                    action_label='Voir les documents'
                ))

            # Documents avec erreur OCR
            erreurs = base_qs.filter(statut_traitement='ERREUR').count()

            if erreurs > 0:
                insights.append(Insight(
                    type=InsightType.WARNING,
                    category=InsightCategory.DOCUMENTS,
                    title=f"{erreurs} document(s) avec erreur",
                    message="Certains documents n'ont pas pu être traités automatiquement.",
                    value=erreurs,
                    priority=40,
                    action_url='/documents/?statut=ERREUR',
                    action_label='Voir les erreurs'
                ))

        except LookupError:
            pass  # App documents non installée

        return insights

    def _insights_salaires(self) -> List[Insight]:
        """Analyse les salaires et charges."""
        insights = []

        try:
            FicheSalaire = apps.get_model('salaires', 'FicheSalaire')

            # Vérifier les fiches du mois en cours
            mois_courant = self.today.replace(day=1)

            base_qs = FicheSalaire.objects.filter(is_active=True)
            if self.mandat:
                base_qs = base_qs.filter(employe__mandat=self.mandat)

            # Fiches non générées ce mois
            fiches_mois = base_qs.filter(
                mois=mois_courant.month,
                annee=mois_courant.year
            ).count()

            # TODO: Comparer avec le nombre d'employés actifs

            # Évolution masse salariale
            trois_mois = self.today - timedelta(days=90)
            masse_recente = base_qs.filter(
                date_paiement__gte=trois_mois
            ).aggregate(total=Sum('salaire_net'))['total'] or Decimal('0')

        except LookupError:
            pass  # App salaires non installée

        return insights


# Instance singleton
insights_engine = InsightsEngine()


def get_dashboard_insights(mandat=None, limit=10) -> List[Dict]:
    """
    Récupère les insights pour le dashboard.

    Args:
        mandat: Filtrer par mandat
        limit: Nombre max d'insights

    Returns:
        Liste de dicts formatés pour le frontend
    """
    engine = InsightsEngine(mandat=mandat)
    insights = engine.generate_all_insights()[:limit]

    return [
        {
            'type': i.type.value,
            'category': i.category.value,
            'title': i.title,
            'message': i.message,
            'value': i.value,
            'reference_value': i.reference_value,
            'change_percent': i.change_percent,
            'priority': i.priority,
            'action_url': i.action_url,
            'action_label': i.action_label,
            'metadata': i.metadata,
        }
        for i in insights
    ]
