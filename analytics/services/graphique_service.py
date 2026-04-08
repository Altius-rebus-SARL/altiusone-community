# analytics/services/graphique_service.py
"""
Service pour la génération des données de graphiques.

Ce service récupère les données comptables et les formate pour les graphiques
selon la configuration du TypeGraphiqueRapport.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from collections import defaultdict

from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth

from analytics.models import TypeGraphiqueRapport
from core.models import Mandat

logger = logging.getLogger(__name__)


class GraphiqueService:
    """Service pour générer les données des graphiques prédéfinis."""

    @classmethod
    def get_donnees_graphique(
        cls,
        type_graphique: TypeGraphiqueRapport,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
    ) -> dict:
        """
        Récupère les données pour un graphique prédéfini.

        Args:
            type_graphique: Le type de graphique prédéfini
            mandat: Le mandat concerné
            date_debut: Date de début de la période
            date_fin: Date de fin de la période

        Returns:
            Dictionnaire avec les données formatées pour le graphique
        """
        config = type_graphique.config_source
        source = config.get('source', '')

        # Router vers la méthode appropriée selon la source
        data_methods = {
            'bilan': cls._get_donnees_bilan,
            'bilan_detail': cls._get_donnees_bilan_detail,
            'compte_resultats': cls._get_donnees_compte_resultats,
            'compte_resultats_detail': cls._get_donnees_compte_resultats_detail,
            'tresorerie': cls._get_donnees_tresorerie,
            'tva': cls._get_donnees_tva,
            'salaires': cls._get_donnees_salaires,
            'chiffre_affaires': cls._get_donnees_chiffre_affaires,
            'rentabilite': cls._get_donnees_rentabilite,
            'balance': cls._get_donnees_balance,
        }

        method = data_methods.get(source)
        if method:
            try:
                return method(mandat, date_debut, date_fin, config, type_graphique)
            except Exception as e:
                logger.exception(f"Erreur récupération données {source}: {e}")
                return cls._donnees_vides(type_graphique)

        logger.warning(f"Source inconnue: {source}")
        return cls._donnees_vides(type_graphique)

    @classmethod
    def _donnees_vides(cls, type_graphique: TypeGraphiqueRapport) -> dict:
        """Retourne une structure de données vide."""
        if type_graphique.type_graphique in ['donut', 'pie']:
            return {'labels': [], 'values': []}
        return {'categories': [], 'series': []}

    # =========================================================================
    # BILAN
    # =========================================================================

    @classmethod
    def _get_donnees_bilan(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données pour graphique de répartition actif/passif."""
        from comptabilite.models import EcritureComptable

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__lte=date_fin,
        )

        # Actifs (classe 1)
        actifs = ecritures.filter(
            compte__classe=1
        ).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        # Passifs (classe 2)
        passifs = ecritures.filter(
            compte__classe=2
        ).aggregate(
            total=Sum(F('montant_credit') - F('montant_debit'))
        )['total'] or Decimal('0')

        return {
            'labels': ['Actifs', 'Passifs'],
            'values': [float(abs(actifs)), float(abs(passifs))],
        }

    @classmethod
    def _get_donnees_bilan_detail(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données détaillées du bilan par catégorie."""
        from comptabilite.models import EcritureComptable, Compte

        filtres = config.get('filtres', {})
        type_bilan = filtres.get('type', 'actif')  # actif ou passif

        classe = 1 if type_bilan == 'actif' else 2

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__lte=date_fin,
            compte__classe=classe,
        ).values(
            'compte__numero',
            'compte__libelle'
        ).annotate(
            solde=Sum(F('montant_debit') - F('montant_credit')) if type_bilan == 'actif' else Sum(F('montant_credit') - F('montant_debit'))
        ).filter(
            solde__gt=0
        ).order_by('-solde')[:10]

        categories = []
        values = []
        for e in ecritures:
            categories.append(e['compte__libelle'][:30])
            values.append(float(abs(e['solde'])))

        return {
            'categories': categories,
            'series': [{'name': 'Montant', 'data': values}],
        }

    # =========================================================================
    # COMPTE DE RÉSULTATS
    # =========================================================================

    @classmethod
    def _get_donnees_compte_resultats(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données pour graphique produits/charges."""
        from comptabilite.models import EcritureComptable

        agregation = config.get('agregation', 'sum')

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
        )

        if agregation == 'sum_by_month':
            # Évolution mensuelle du résultat net (produits - charges par mois)
            # Produits par mois
            produits_par_mois = ecritures.filter(
                compte__classe__in=[3, 7]
            ).annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                total=Sum(F('montant_credit') - F('montant_debit'))
            )

            # Charges par mois
            charges_par_mois = ecritures.filter(
                compte__classe__in=[4, 5, 6, 8]
            ).annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                total=Sum(F('montant_debit') - F('montant_credit'))
            )

            # Combiner par mois
            par_mois = defaultdict(lambda: {'produits': Decimal('0'), 'charges': Decimal('0')})
            for p in produits_par_mois:
                if p['mois']:
                    par_mois[p['mois']]['produits'] = p['total'] or Decimal('0')
            for c in charges_par_mois:
                if c['mois']:
                    par_mois[c['mois']]['charges'] = c['total'] or Decimal('0')

            if not par_mois:
                return cls._donnees_vides(type_graphique)

            categories = []
            resultats = []
            for mois in sorted(par_mois.keys()):
                categories.append(mois.strftime('%b %Y'))
                resultat_net = par_mois[mois]['produits'] - par_mois[mois]['charges']
                resultats.append(float(resultat_net))

            return {
                'categories': categories,
                'series': [{'name': 'Résultat net', 'data': resultats}],
            }

        # Format par défaut: donut/pie (produits vs charges total)
        # Produits (classes 3, 7)
        produits = ecritures.filter(
            compte__classe__in=[3, 7]
        ).aggregate(
            total=Sum(F('montant_credit') - F('montant_debit'))
        )['total'] or Decimal('0')

        # Charges (classes 4, 5, 6, 8)
        charges = ecritures.filter(
            compte__classe__in=[4, 5, 6, 8]
        ).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        return {
            'labels': ['Produits', 'Charges'],
            'values': [float(abs(produits)), float(abs(charges))],
        }

    @classmethod
    def _get_donnees_compte_resultats_detail(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Top 10 des comptes de produits ou charges."""
        from comptabilite.models import EcritureComptable

        filtres = config.get('filtres', {})
        type_cr = filtres.get('type', 'produit')

        if type_cr == 'produit':
            classes = [3, 7]
            calcul = F('montant_credit') - F('montant_debit')
        else:
            classes = [4, 5, 6, 8]
            calcul = F('montant_debit') - F('montant_credit')

        limite = config.get('limite', 10)

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
            compte__classe__in=classes,
        ).values(
            'compte__numero',
            'compte__libelle'
        ).annotate(
            montant=Sum(calcul)
        ).filter(
            montant__gt=0
        ).order_by('-montant')[:limite]

        categories = []
        values = []
        for e in ecritures:
            categories.append(e['compte__libelle'][:30])
            values.append(float(e['montant']))

        return {
            'categories': categories,
            'series': [{'name': 'Montant', 'data': values}],
        }

    # =========================================================================
    # TRÉSORERIE
    # =========================================================================

    @classmethod
    def _get_donnees_tresorerie(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données de trésorerie (évolution ou encaissements/décaissements)."""
        from comptabilite.models import EcritureComptable

        agregation = config.get('agregation', 'cumul_by_date')

        # Comptes de trésorerie (1000-1099)
        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
            compte__numero__startswith='10',
        )

        if agregation == 'cumul_by_date':
            # Évolution cumulative
            mouvements = ecritures.annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                mouvement=Sum(F('montant_debit') - F('montant_credit'))
            ).order_by('mois')

            categories = []
            values = []
            cumul = Decimal('0')

            for m in mouvements:
                categories.append(m['mois'].strftime('%b %Y'))
                cumul += m['mouvement']
                values.append(float(cumul))

            return {
                'categories': categories,
                'series': [{'name': 'Solde', 'data': values}],
            }

        elif agregation == 'sum_by_month':
            # Encaissements vs décaissements par mois
            mouvements = ecritures.annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                encaissements=Sum('montant_debit'),
                decaissements=Sum('montant_credit'),
            ).order_by('mois')

            categories = []
            encaissements = []
            decaissements = []

            for m in mouvements:
                categories.append(m['mois'].strftime('%b %Y'))
                encaissements.append(float(m['encaissements'] or 0))
                decaissements.append(float(m['decaissements'] or 0))

            return {
                'categories': categories,
                'series': [
                    {'name': 'Encaissements', 'data': encaissements},
                    {'name': 'Décaissements', 'data': decaissements},
                ],
            }

        return cls._donnees_vides(type_graphique)

    # =========================================================================
    # TVA
    # =========================================================================

    @classmethod
    def _get_donnees_tva(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données TVA."""
        from comptabilite.models import EcritureComptable

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
        )

        # TVA collectée — résolu via ConfigurationTVA ou CompteParDefaut, fallback 2200
        compte_tva_due = '2200'
        compte_tva_prealable = '1170'
        try:
            config_tva = mandat.config_tva
            if config_tva.compte_tva_due_id:
                compte_tva_due = config_tva.compte_tva_due.numero
            if config_tva.compte_tva_prealable_id:
                compte_tva_prealable = config_tva.compte_tva_prealable.numero
        except Exception:
            pass

        tva_collectee = ecritures.filter(
            compte__numero__startswith=compte_tva_due
        ).aggregate(
            total=Sum(F('montant_credit') - F('montant_debit'))
        )['total'] or Decimal('0')

        tva_deductible = ecritures.filter(
            compte__numero__startswith=compte_tva_prealable
        ).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        agregation = config.get('agregation', 'sum')

        if agregation == 'sum':
            return {
                'labels': ['TVA collectée', 'TVA déductible'],
                'values': [float(abs(tva_collectee)), float(abs(tva_deductible))],
            }

        elif agregation == 'sum_by_month':
            # TVA nette par mois
            mouvements_collectee = ecritures.filter(
                compte__numero__startswith=compte_tva_due
            ).annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                total=Sum(F('montant_credit') - F('montant_debit'))
            )

            mouvements_deductible = ecritures.filter(
                compte__numero__startswith=compte_tva_prealable
            ).annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                total=Sum(F('montant_debit') - F('montant_credit'))
            )

            # Combiner par mois
            par_mois = defaultdict(lambda: {'collectee': 0, 'deductible': 0})
            for m in mouvements_collectee:
                par_mois[m['mois']]['collectee'] = float(m['total'] or 0)
            for m in mouvements_deductible:
                par_mois[m['mois']]['deductible'] = float(m['total'] or 0)

            categories = []
            values = []
            for mois in sorted(par_mois.keys()):
                categories.append(mois.strftime('%b %Y'))
                tva_nette = par_mois[mois]['collectee'] - par_mois[mois]['deductible']
                values.append(tva_nette)

            return {
                'categories': categories,
                'series': [{'name': 'TVA nette', 'data': values}],
            }

        return cls._donnees_vides(type_graphique)

    # =========================================================================
    # SALAIRES
    # =========================================================================

    @classmethod
    def _get_donnees_salaires(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données des salaires."""
        from salaires.models import FicheSalaire

        fiches = FicheSalaire.objects.filter(
            employe__mandat=mandat,
            date_debut__gte=date_debut,
            date_fin__lte=date_fin,
        )

        agregation = config.get('agregation', 'sum')
        grouper_par = config.get('grouper_par', 'employe')

        if grouper_par == 'employe':
            # Par employé
            par_employe = fiches.values(
                'employe__prenom',
                'employe__nom'
            ).annotate(
                total=Sum('salaire_brut')
            ).order_by('-total')

            labels = []
            values = []
            for e in par_employe:
                labels.append(f"{e['employe__prenom']} {e['employe__nom']}"[:20])
                values.append(float(e['total'] or 0))

            return {
                'labels': labels,
                'values': values,
            }

        elif grouper_par == 'type_cotisation':
            # Par type de cotisation
            cotisations = {
                'AVS/AI/APG': Decimal('0'),
                'AC': Decimal('0'),
                'LAA': Decimal('0'),
                'LPP': Decimal('0'),
                'Autres': Decimal('0'),
            }

            for fiche in fiches:
                cotisations['AVS/AI/APG'] += fiche.cotisation_avs_employe or Decimal('0')
                cotisations['AC'] += fiche.cotisation_ac_employe or Decimal('0')
                cotisations['LAA'] += fiche.cotisation_laa_employe or Decimal('0')
                cotisations['LPP'] += fiche.cotisation_lpp_employe or Decimal('0')

            return {
                'labels': list(cotisations.keys()),
                'values': [float(v) for v in cotisations.values()],
            }

        elif agregation == 'sum_by_month':
            # Évolution mensuelle
            par_mois = fiches.annotate(
                mois=TruncMonth('date_debut')
            ).values('mois').annotate(
                total=Sum('salaire_brut')
            ).order_by('mois')

            categories = []
            values = []
            for m in par_mois:
                categories.append(m['mois'].strftime('%b %Y'))
                values.append(float(m['total'] or 0))

            return {
                'categories': categories,
                'series': [{'name': 'Masse salariale', 'data': values}],
            }

        return cls._donnees_vides(type_graphique)

    # =========================================================================
    # CHIFFRE D'AFFAIRES
    # =========================================================================

    @classmethod
    def _get_donnees_chiffre_affaires(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données du chiffre d'affaires."""
        from comptabilite.models import EcritureComptable

        # CA = classe 3
        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
            compte__classe=3,
        )

        agregation = config.get('agregation', 'sum_by_month')
        comparatif = config.get('comparatif', False)

        if agregation == 'sum_by_month':
            par_mois = ecritures.annotate(
                mois=TruncMonth('date_ecriture')
            ).values('mois').annotate(
                ca=Sum(F('montant_credit') - F('montant_debit'))
            ).order_by('mois')

            categories = []
            values = []
            for m in par_mois:
                categories.append(m['mois'].strftime('%b %Y'))
                values.append(float(m['ca'] or 0))

            if comparatif:
                # Ajouter N-1
                from dateutil.relativedelta import relativedelta
                date_debut_n1 = date_debut - relativedelta(years=1)
                date_fin_n1 = date_fin - relativedelta(years=1)

                ecritures_n1 = EcritureComptable.objects.filter(
                    mandat=mandat,
                    date_ecriture__gte=date_debut_n1,
                    date_ecriture__lte=date_fin_n1,
                    compte__classe=3,
                )

                par_mois_n1 = ecritures_n1.annotate(
                    mois=TruncMonth('date_ecriture')
                ).values('mois').annotate(
                    ca=Sum(F('montant_credit') - F('montant_debit'))
                ).order_by('mois')

                values_n1 = []
                for m in par_mois_n1:
                    values_n1.append(float(m['ca'] or 0))

                return {
                    'categories': categories,
                    'series': [
                        {'name': 'Année N', 'data': values},
                        {'name': 'Année N-1', 'data': values_n1},
                    ],
                }

            return {
                'categories': categories,
                'series': [{'name': 'Chiffre d\'affaires', 'data': values}],
            }

        return cls._donnees_vides(type_graphique)

    # =========================================================================
    # RENTABILITÉ
    # =========================================================================

    @classmethod
    def _get_donnees_rentabilite(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données de rentabilité (marges)."""
        from comptabilite.models import EcritureComptable

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__gte=date_debut,
            date_ecriture__lte=date_fin,
        )

        # CA (classe 3)
        ca = ecritures.filter(compte__classe=3).aggregate(
            total=Sum(F('montant_credit') - F('montant_debit'))
        )['total'] or Decimal('0')

        # Coût des ventes (classe 4)
        cout_ventes = ecritures.filter(compte__classe=4).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        # Charges d'exploitation (classes 5, 6)
        charges_exploitation = ecritures.filter(compte__classe__in=[5, 6]).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        # Charges financières et autres (classe 8)
        autres_charges = ecritures.filter(compte__classe=8).aggregate(
            total=Sum(F('montant_debit') - F('montant_credit'))
        )['total'] or Decimal('0')

        # Calcul des marges
        marge_brute = ca - cout_ventes
        resultat_exploitation = marge_brute - charges_exploitation
        resultat_net = resultat_exploitation - autres_charges

        # En pourcentage
        if ca > 0:
            marge_brute_pct = float(marge_brute / ca * 100)
            marge_exploitation_pct = float(resultat_exploitation / ca * 100)
            marge_nette_pct = float(resultat_net / ca * 100)
        else:
            marge_brute_pct = marge_exploitation_pct = marge_nette_pct = 0

        agregation = config.get('agregation', 'ratio')

        if agregation == 'ratio':
            return {
                'categories': ['Marge brute', 'Marge opérationnelle', 'Marge nette'],
                'series': [{
                    'name': 'Pourcentage',
                    'data': [marge_brute_pct, marge_exploitation_pct, marge_nette_pct]
                }],
            }

        return cls._donnees_vides(type_graphique)

    # =========================================================================
    # BALANCE
    # =========================================================================

    @classmethod
    def _get_donnees_balance(
        cls,
        mandat: Mandat,
        date_debut: date,
        date_fin: date,
        config: dict,
        type_graphique: TypeGraphiqueRapport,
    ) -> dict:
        """Données de la balance des comptes."""
        from comptabilite.models import EcritureComptable

        ecritures = EcritureComptable.objects.filter(
            mandat=mandat,
            date_ecriture__lte=date_fin,
        )

        agregation = config.get('agregation', 'sum')
        grouper_par = config.get('grouper_par', 'classe')

        if grouper_par == 'classe':
            # Par classe
            par_classe = ecritures.values(
                'compte__classe'
            ).annotate(
                debit=Sum('montant_debit'),
                credit=Sum('montant_credit'),
            ).order_by('compte__classe')

            noms_classes = {
                1: 'Actifs',
                2: 'Passifs',
                3: 'Produits expl.',
                4: 'Achats',
                5: 'Frais personnel',
                6: 'Autres charges',
                7: 'Produits financ.',
                8: 'Charges except.',
                9: 'Clôture',
            }

            categories = []
            values = []
            for c in par_classe:
                classe = c['compte__classe']
                if classe:
                    categories.append(noms_classes.get(classe, f'Classe {classe}'))
                    solde = abs(float((c['debit'] or 0) - (c['credit'] or 0)))
                    values.append(solde)

            return {
                'categories': categories,
                'series': [{'name': 'Solde', 'data': values}],
            }

        elif agregation == 'top':
            # Top comptes
            filtres = config.get('filtres', {})
            solde_type = filtres.get('solde_type', 'debiteur')
            limite = config.get('limite', 10)

            par_compte = ecritures.values(
                'compte__numero',
                'compte__libelle'
            ).annotate(
                debit=Sum('montant_debit'),
                credit=Sum('montant_credit'),
            )

            # Filtrer et trier
            resultats = []
            for c in par_compte:
                solde = (c['debit'] or 0) - (c['credit'] or 0)
                if solde_type == 'debiteur' and solde > 0:
                    resultats.append((c['compte__libelle'], float(solde)))
                elif solde_type == 'crediteur' and solde < 0:
                    resultats.append((c['compte__libelle'], float(abs(solde))))

            resultats.sort(key=lambda x: x[1], reverse=True)
            resultats = resultats[:limite]

            categories = [r[0][:30] for r in resultats]
            values = [r[1] for r in resultats]

            return {
                'categories': categories,
                'series': [{'name': 'Solde', 'data': values}],
            }

        return cls._donnees_vides(type_graphique)
