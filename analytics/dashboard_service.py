# analytics/dashboard_service.py
"""
Service de données pour le Dashboard Exécutif.

Agrège les données de toutes les applications Django pour alimenter
les graphiques et KPIs du tableau de bord fiduciaire.
"""
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Avg, Count, Q, F, Case, When, Value, CharField
from django.db.models.functions import TruncMonth, ExtractMonth, ExtractYear
from django.apps import apps
from collections import defaultdict


class DashboardDataService:
    """
    Service centralisé pour récupérer les données du dashboard exécutif.

    Fournit des méthodes optimisées pour:
    - KPIs principaux (CA, recouvrement, encours, etc.)
    - Données de graphiques (évolutions, répartitions)
    - Analyses avancées (Pareto, aging, tendances)
    """

    def __init__(self, user=None, mandat=None, annee=None):
        self.user = user
        self.mandat = mandat
        self.annee = annee or date.today().year
        self.today = date.today()

        # Périodes de référence
        self.debut_annee = date(self.annee, 1, 1)
        self.fin_annee = date(self.annee, 12, 31)
        self.debut_mois = self.today.replace(day=1)
        self.mois_precedent = self.debut_mois - relativedelta(months=1)

    def get_kpis_principaux(self):
        """
        Retourne les KPIs principaux pour les cartes du dashboard.

        Returns:
            dict: {
                'ca_mensuel': {'valeur': Decimal, 'evolution': float, 'tendance': [...]},
                'ca_annuel': {'valeur': Decimal, 'evolution': float},
                'taux_recouvrement': {'valeur': float, 'objectif': float},
                'encours_clients': {'valeur': Decimal, 'nb_factures': int},
                'factures_impayees': {'valeur': int, 'montant': Decimal},
                'dso': {'valeur': float, 'evolution': float},
                'heures_facturees': {'valeur': Decimal, 'evolution': float},
                'nb_clients_actifs': {'valeur': int},
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        # Base queryset avec filtrage mandat si applicable
        factures_qs = Facture.objects.all()
        if self.mandat:
            factures_qs = factures_qs.filter(mandat=self.mandat)

        # CA Mensuel
        ca_mois_actuel = factures_qs.filter(
            date_emission__gte=self.debut_mois,
            date_emission__lte=self.today,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        ca_mois_precedent = factures_qs.filter(
            date_emission__gte=self.mois_precedent,
            date_emission__lt=self.debut_mois,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        evolution_ca_mensuel = self._calcul_evolution(ca_mois_actuel, ca_mois_precedent)

        # Tendance CA (12 derniers mois pour sparkline)
        tendance_ca = self._get_tendance_ca_mensuel(factures_qs, 12)

        # CA Annuel
        ca_annuel = factures_qs.filter(
            date_emission__gte=self.debut_annee,
            date_emission__lte=self.today,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        ca_annee_precedente = factures_qs.filter(
            date_emission__gte=date(self.annee - 1, 1, 1),
            date_emission__lte=date(self.annee - 1, self.today.month, self.today.day),
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        evolution_ca_annuel = self._calcul_evolution(ca_annuel, ca_annee_precedente)

        # Taux de recouvrement
        factures_periode = factures_qs.filter(
            date_emission__gte=self.debut_annee,
            date_emission__lte=self.today,
        )
        montant_facture = factures_periode.aggregate(Sum('montant_ttc'))['montant_ttc__sum'] or Decimal('0')
        montant_paye = factures_periode.aggregate(Sum('montant_paye'))['montant_paye__sum'] or Decimal('0')
        taux_recouvrement = float((montant_paye / montant_facture * 100)) if montant_facture > 0 else 100

        # Encours clients
        encours_qs = factures_qs.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE', 'EN_RETARD', 'PARTIELLEMENT_PAYEE'],
            montant_restant__gt=0
        )
        encours_total = encours_qs.aggregate(total=Sum('montant_restant'))['total'] or Decimal('0')
        nb_factures_encours = encours_qs.count()

        # Factures impayées en retard
        factures_retard = factures_qs.filter(
            statut='EN_RETARD',
            montant_restant__gt=0
        )
        nb_impayees = factures_retard.count()
        montant_impayees = factures_retard.aggregate(total=Sum('montant_restant'))['total'] or Decimal('0')

        # DSO (Délai moyen de paiement)
        dso = self._calcul_dso(factures_qs)

        # Heures facturées
        heures_data = self._get_heures_facturees()

        # Clients actifs
        nb_clients = factures_qs.filter(
            date_emission__gte=self.debut_annee,
            date_emission__lte=self.today,
        ).values('client').distinct().count()

        return {
            'ca_mensuel': {
                'valeur': ca_mois_actuel,
                'evolution': evolution_ca_mensuel,
                'tendance': tendance_ca,
            },
            'ca_annuel': {
                'valeur': ca_annuel,
                'evolution': evolution_ca_annuel,
            },
            'taux_recouvrement': {
                'valeur': round(taux_recouvrement, 1),
                'objectif': 95,  # Objectif standard fiduciaire
            },
            'encours_clients': {
                'valeur': encours_total,
                'nb_factures': nb_factures_encours,
            },
            'factures_impayees': {
                'valeur': nb_impayees,
                'montant': montant_impayees,
            },
            'dso': {
                'valeur': dso['moyen'],
                'evolution': dso['evolution'],
            },
            'heures_facturees': heures_data,
            'nb_clients_actifs': {
                'valeur': nb_clients,
            },
        }

    def get_evolution_ca_mensuel(self, nb_mois=12, comparer_n1=True):
        """
        Données pour le graphique d'évolution du CA.

        Returns:
            dict: {
                'categories': ['Jan', 'Fév', ...],
                'series': [
                    {'name': '2024', 'data': [...]},
                    {'name': '2023', 'data': [...]}  # Si comparer_n1
                ]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        factures_qs = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )
        if self.mandat:
            factures_qs = factures_qs.filter(mandat=self.mandat)

        # CA par mois année courante
        ca_par_mois = factures_qs.filter(
            date_emission__year=self.annee
        ).annotate(
            mois=ExtractMonth('date_emission')
        ).values('mois').annotate(
            total=Sum('montant_ht')
        ).order_by('mois')

        # Construire les données
        mois_labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                       'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        data_annee = [0] * 12
        for item in ca_par_mois:
            data_annee[item['mois'] - 1] = float(item['total'] or 0)

        series = [{'name': str(self.annee), 'data': data_annee}]

        # Année N-1 pour comparaison
        if comparer_n1:
            ca_n1 = factures_qs.filter(
                date_emission__year=self.annee - 1
            ).annotate(
                mois=ExtractMonth('date_emission')
            ).values('mois').annotate(
                total=Sum('montant_ht')
            ).order_by('mois')

            data_n1 = [0] * 12
            for item in ca_n1:
                data_n1[item['mois'] - 1] = float(item['total'] or 0)

            series.append({'name': str(self.annee - 1), 'data': data_n1})

        return {
            'categories': mois_labels,
            'series': series,
        }

    def get_repartition_ca_type_prestation(self):
        """
        Répartition du CA par type de prestation (donut chart).

        Returns:
            dict: {
                'labels': ['Comptabilité', 'TVA', ...],
                'series': [45000, 20000, ...]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')
        LigneFacture = apps.get_model('facturation', 'LigneFacture')

        lignes_qs = LigneFacture.objects.filter(
            facture__date_emission__year=self.annee,
            facture__statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )
        if self.mandat:
            lignes_qs = lignes_qs.filter(facture__mandat=self.mandat)

        repartition = lignes_qs.values(
            'prestation__type_prestation'
        ).annotate(
            total=Sum(F('quantite') * F('prix_unitaire_ht'))
        ).order_by('-total')

        # Labels traduits
        type_labels = {
            'COMPTABILITE': 'Comptabilité',
            'TVA': 'TVA',
            'SALAIRES': 'Salaires',
            'CONSEIL': 'Conseil',
            'AUDIT': 'Audit',
            'FISCALITE': 'Fiscalité',
            'JURIDIQUE': 'Juridique',
            'CREATION': 'Création',
            'AUTRE': 'Autres',
        }

        labels = []
        series = []
        for item in repartition:
            type_code = item['prestation__type_prestation']
            if type_code:
                labels.append(type_labels.get(type_code, type_code))
                series.append(float(item['total'] or 0))

        return {'labels': labels, 'series': series}

    def get_top_clients(self, limit=10):
        """
        Top clients par CA (bar chart horizontal).

        Returns:
            dict: {
                'categories': ['Client A', 'Client B', ...],
                'series': [{'name': 'CA', 'data': [...]}]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        top_clients = Facture.objects.filter(
            date_emission__year=self.annee,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )
        if self.mandat:
            top_clients = top_clients.filter(mandat=self.mandat)

        top_clients = top_clients.values(
            'client__raison_sociale'
        ).annotate(
            total=Sum('montant_ht')
        ).order_by('-total')[:limit]

        categories = []
        data = []
        for item in top_clients:
            nom = item['client__raison_sociale'] or 'Client inconnu'
            # Tronquer les noms longs
            categories.append(nom[:30] + '...' if len(nom) > 30 else nom)
            data.append(float(item['total'] or 0))

        return {
            'categories': categories,
            'series': [{'name': 'CA', 'data': data}]
        }

    def get_aging_analysis(self):
        """
        Analyse de l'ancienneté des créances (stacked bar).

        Returns:
            dict: {
                'categories': ['0-30j', '31-60j', '61-90j', '90+j'],
                'series': [
                    {'name': 'Montant', 'data': [...]}
                ]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        factures_ouvertes = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE', 'EN_RETARD', 'PARTIELLEMENT_PAYEE'],
            montant_restant__gt=0
        )
        if self.mandat:
            factures_ouvertes = factures_ouvertes.filter(mandat=self.mandat)

        # Catégoriser par ancienneté
        aging = {'0-30j': Decimal('0'), '31-60j': Decimal('0'),
                 '61-90j': Decimal('0'), '90+j': Decimal('0')}

        for facture in factures_ouvertes:
            jours = (self.today - facture.date_emission).days
            if jours <= 30:
                aging['0-30j'] += facture.montant_restant
            elif jours <= 60:
                aging['31-60j'] += facture.montant_restant
            elif jours <= 90:
                aging['61-90j'] += facture.montant_restant
            else:
                aging['90+j'] += facture.montant_restant

        return {
            'categories': list(aging.keys()),
            'series': [
                {'name': 'Encours', 'data': [float(v) for v in aging.values()]}
            ]
        }

    def get_pareto_clients(self):
        """
        Analyse Pareto 80/20 des clients.

        Returns:
            dict: {
                'categories': ['Client 1', ...],
                'series': [
                    {'name': 'CA', 'type': 'bar', 'data': [...]},
                    {'name': '% Cumulé', 'type': 'line', 'data': [...]}
                ]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        clients_ca = Facture.objects.filter(
            date_emission__year=self.annee,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )
        if self.mandat:
            clients_ca = clients_ca.filter(mandat=self.mandat)

        clients_ca = clients_ca.values(
            'client__raison_sociale'
        ).annotate(
            total=Sum('montant_ht')
        ).order_by('-total')

        # Calcul du % cumulé
        ca_total = sum(float(c['total'] or 0) for c in clients_ca)
        if ca_total == 0:
            return {'categories': [], 'series': []}

        categories = []
        ca_data = []
        cumule_data = []
        cumul = 0

        for item in clients_ca[:20]:  # Top 20 pour lisibilité
            nom = item['client__raison_sociale'] or 'Inconnu'
            categories.append(nom[:20] if len(nom) > 20 else nom)
            ca = float(item['total'] or 0)
            ca_data.append(ca)
            cumul += ca
            cumule_data.append(round(cumul / ca_total * 100, 1))

        return {
            'categories': categories,
            'series': [
                {'name': 'CA', 'type': 'bar', 'data': ca_data},
                {'name': '% Cumulé', 'type': 'line', 'data': cumule_data}
            ]
        }

    def get_treemap_mandats(self):
        """
        Treemap du CA par type de mandat.

        Returns:
            dict: {
                'series': [{
                    'data': [{'x': 'Comptabilité', 'y': 50000}, ...]
                }]
            }
        """
        Facture = apps.get_model('facturation', 'Facture')

        ca_par_mandat = Facture.objects.filter(
            date_emission__year=self.annee,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).values(
            'mandat__type_mandat'
        ).annotate(
            total=Sum('montant_ht')
        ).order_by('-total')

        type_labels = {
            'COMPTA': 'Comptabilité',
            'TVA': 'TVA',
            'SALAIRES': 'Salaires',
            'FISCAL': 'Fiscal',
            'REVISION': 'Révision',
            'CONSEIL': 'Conseil',
            'CREATION': 'Création',
            'GLOBAL': 'Global',
        }

        data = []
        for item in ca_par_mandat:
            type_code = item['mandat__type_mandat']
            if type_code and item['total']:
                data.append({
                    'x': type_labels.get(type_code, type_code),
                    'y': float(item['total'])
                })

        return {'series': [{'data': data}]}

    def get_alertes_dashboard(self):
        """
        Alertes et points d'attention pour le dashboard.

        Returns:
            list: [{'type': 'danger|warning|info', 'message': str, 'count': int}]
        """
        Facture = apps.get_model('facturation', 'Facture')
        alertes = []

        # Factures en retard critique (> 90 jours)
        critiques = Facture.objects.filter(
            statut='EN_RETARD',
            date_echeance__lt=self.today - timedelta(days=90),
            montant_restant__gt=0
        )
        if self.mandat:
            critiques = critiques.filter(mandat=self.mandat)
        nb_critiques = critiques.count()

        if nb_critiques > 0:
            montant = critiques.aggregate(Sum('montant_restant'))['montant_restant__sum']
            alertes.append({
                'type': 'danger',
                'icon': 'ti-alert-triangle',
                'message': f'{nb_critiques} facture(s) en retard critique (>90j)',
                'montant': float(montant or 0),
                'action_url': '/facturation/factures/?statut=EN_RETARD',
            })

        # Échéances proches (7 jours)
        echeances_proches = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE'],
            date_echeance__gte=self.today,
            date_echeance__lte=self.today + timedelta(days=7),
            montant_restant__gt=0
        )
        if self.mandat:
            echeances_proches = echeances_proches.filter(mandat=self.mandat)
        nb_echeances = echeances_proches.count()

        if nb_echeances > 0:
            montant = echeances_proches.aggregate(Sum('montant_restant'))['montant_restant__sum']
            alertes.append({
                'type': 'warning',
                'icon': 'ti-clock',
                'message': f'{nb_echeances} facture(s) arrivent à échéance cette semaine',
                'montant': float(montant or 0),
                'action_url': '/facturation/factures/',
            })

        # Taux de recouvrement bas
        kpis = self.get_kpis_principaux()
        if kpis['taux_recouvrement']['valeur'] < 85:
            alertes.append({
                'type': 'warning',
                'icon': 'ti-trending-down',
                'message': f"Taux de recouvrement faible ({kpis['taux_recouvrement']['valeur']}%)",
                'action_url': '/analytics/alertes/',
            })

        return alertes

    def get_full_dashboard_data(self):
        """
        Retourne toutes les données nécessaires au dashboard en un seul appel.

        Optimisé pour minimiser les requêtes DB.
        """
        return {
            'kpis': self.get_kpis_principaux(),
            'evolution_ca': self.get_evolution_ca_mensuel(),
            'repartition_prestation': self.get_repartition_ca_type_prestation(),
            'top_clients': self.get_top_clients(),
            'aging': self.get_aging_analysis(),
            'alertes': self.get_alertes_dashboard(),
        }

    # ===== Méthodes privées =====

    def _calcul_evolution(self, actuel, precedent):
        """Calcule le % d'évolution entre deux valeurs."""
        if precedent and precedent > 0:
            return round(float((actuel - precedent) / precedent * 100), 1)
        return 0

    def _get_tendance_ca_mensuel(self, factures_qs, nb_mois=12):
        """Retourne la tendance CA pour sparkline."""
        tendance = []
        for i in range(nb_mois - 1, -1, -1):
            debut = (self.today - relativedelta(months=i)).replace(day=1)
            if i > 0:
                fin = (self.today - relativedelta(months=i - 1)).replace(day=1) - timedelta(days=1)
            else:
                fin = self.today

            ca = factures_qs.filter(
                date_emission__gte=debut,
                date_emission__lte=fin,
                statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
            ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

            tendance.append(float(ca))

        return tendance

    def _calcul_dso(self, factures_qs):
        """Calcule le DSO (Days Sales Outstanding)."""
        factures_payees = factures_qs.filter(
            statut='PAYEE',
            date_paiement_complet__isnull=False,
            date_emission__gte=self.today - timedelta(days=365),
        )

        delais = []
        for f in factures_payees:
            if f.date_paiement_complet and f.date_emission:
                delais.append((f.date_paiement_complet - f.date_emission).days)

        dso_moyen = sum(delais) / len(delais) if delais else 0

        # Évolution vs période précédente (6 derniers mois vs 6 mois avant)
        factures_recentes = factures_qs.filter(
            statut='PAYEE',
            date_paiement_complet__isnull=False,
            date_emission__gte=self.today - timedelta(days=180),
        )
        factures_anciennes = factures_qs.filter(
            statut='PAYEE',
            date_paiement_complet__isnull=False,
            date_emission__gte=self.today - timedelta(days=360),
            date_emission__lt=self.today - timedelta(days=180),
        )

        delais_recents = []
        for f in factures_recentes:
            if f.date_paiement_complet and f.date_emission:
                delais_recents.append((f.date_paiement_complet - f.date_emission).days)

        delais_anciens = []
        for f in factures_anciennes:
            if f.date_paiement_complet and f.date_emission:
                delais_anciens.append((f.date_paiement_complet - f.date_emission).days)

        dso_recent = sum(delais_recents) / len(delais_recents) if delais_recents else 0
        dso_ancien = sum(delais_anciens) / len(delais_anciens) if delais_anciens else dso_recent

        evolution = self._calcul_evolution(Decimal(str(dso_recent)), Decimal(str(dso_ancien)))

        return {'moyen': round(dso_moyen, 0), 'evolution': evolution}

    def _get_heures_facturees(self):
        """Récupère les heures facturées du mois."""
        try:
            TimeTracking = apps.get_model('facturation', 'TimeTracking')

            qs = TimeTracking.objects.filter(
                date_travail__gte=self.debut_mois,
                date_travail__lte=self.today,
                facturable=True
            )
            if self.mandat:
                qs = qs.filter(mandat=self.mandat)

            heures_mois = qs.aggregate(total=Sum('duree_minutes'))['total'] or 0
            heures = Decimal(str(heures_mois)) / 60

            # Mois précédent
            qs_prec = TimeTracking.objects.filter(
                date_travail__gte=self.mois_precedent,
                date_travail__lt=self.debut_mois,
                facturable=True
            )
            if self.mandat:
                qs_prec = qs_prec.filter(mandat=self.mandat)

            heures_prec = (qs_prec.aggregate(total=Sum('duree_minutes'))['total'] or 0) / 60

            return {
                'valeur': heures,
                'evolution': self._calcul_evolution(heures, Decimal(str(heures_prec)))
            }
        except Exception:
            return {'valeur': Decimal('0'), 'evolution': 0}
