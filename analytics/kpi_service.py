# analytics/services.py
"""
Services de calcul des KPI et indicateurs.
"""
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Avg, Count, Q, F
from django.apps import apps


class KPICalculator:
    """
    Calculateur de KPI.

    Calcule les valeurs des indicateurs selon leur configuration.
    """

    def __init__(self, mandat=None, date_debut=None, date_fin=None):
        self.mandat = mandat
        self.date_debut = date_debut or date.today().replace(day=1)
        self.date_fin = date_fin or date.today()

    def calculer_kpi(self, indicateur):
        """
        Calcule la valeur d'un indicateur.

        Args:
            indicateur: Instance de Indicateur

        Returns:
            dict: {valeur, details, periode_debut, periode_fin}
        """
        # Déterminer la méthode de calcul
        methode_map = {
            'ca_mensuel': self._calcul_ca_mensuel,
            'ca_annuel': self._calcul_ca_annuel,
            'marge_brute': self._calcul_marge_brute,
            'taux_marge': self._calcul_taux_marge,
            'encours_clients': self._calcul_encours_clients,
            'delai_paiement_moyen': self._calcul_delai_paiement_moyen,
            'factures_impayees': self._calcul_factures_impayees,
            'taux_recouvrement': self._calcul_taux_recouvrement,
            'nb_clients_actifs': self._calcul_nb_clients_actifs,
            'nb_factures_mois': self._calcul_nb_factures_mois,
            'heures_facturees': self._calcul_heures_facturees,
            'taux_occupation': self._calcul_taux_occupation,
            'masse_salariale': self._calcul_masse_salariale,
            'charges_sociales': self._calcul_charges_sociales,
            'tresorerie_nette': self._calcul_tresorerie_nette,
            'ratio_liquidite': self._calcul_ratio_liquidite,
            'evolution_ca': self._calcul_evolution_ca,
        }

        code = indicateur.code.lower()

        if code in methode_map:
            return methode_map[code]()
        elif indicateur.type_calcul == 'CUSTOM' and indicateur.formule:
            return self._calcul_formule_custom(indicateur)
        elif indicateur.source_table and indicateur.source_champ:
            return self._calcul_depuis_source(indicateur)
        else:
            return {'valeur': Decimal('0'), 'details': {'erreur': 'Méthode non implémentée'}}

    def _get_factures(self):
        """Récupère les factures du mandat pour la période"""
        Facture = apps.get_model('facturation', 'Facture')

        queryset = Facture.objects.filter(
            date_emission__gte=self.date_debut,
            date_emission__lte=self.date_fin,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        return queryset

    def _calcul_ca_mensuel(self):
        """Chiffre d'affaires mensuel"""
        factures = self._get_factures()
        total = factures.aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        return {
            'valeur': total,
            'details': {
                'nb_factures': factures.count(),
                'montant_ttc': factures.aggregate(Sum('montant_ttc'))['montant_ttc__sum'] or 0,
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_ca_annuel(self):
        """Chiffre d'affaires annuel"""
        annee_debut = self.date_fin.replace(month=1, day=1)

        Facture = apps.get_model('facturation', 'Facture')
        queryset = Facture.objects.filter(
            date_emission__gte=annee_debut,
            date_emission__lte=self.date_fin,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        total = queryset.aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')

        return {
            'valeur': total,
            'details': {
                'nb_factures': queryset.count(),
                'annee': self.date_fin.year,
            },
            'periode_debut': annee_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_marge_brute(self):
        """Marge brute = CA - Achats"""
        ca = self._calcul_ca_mensuel()['valeur']

        # Récupérer les achats depuis la comptabilité
        try:
            EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
            achats = EcritureComptable.objects.filter(
                compte__numero__startswith='4',  # Comptes de charges
                date_ecriture__gte=self.date_debut,
                date_ecriture__lte=self.date_fin,
                statut='VALIDE'
            )
            if self.mandat:
                achats = achats.filter(mandat=self.mandat)

            total_achats = achats.aggregate(
                total=Sum('montant_debit') - Sum('montant_credit')
            )['total'] or Decimal('0')
        except Exception:
            total_achats = Decimal('0')

        marge = ca - abs(total_achats)

        return {
            'valeur': marge,
            'details': {
                'chiffre_affaires': float(ca),
                'achats': float(total_achats),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_taux_marge(self):
        """Taux de marge = Marge / CA * 100"""
        marge_data = self._calcul_marge_brute()
        ca = marge_data['details']['chiffre_affaires']
        marge = marge_data['valeur']

        if ca > 0:
            taux = (marge / Decimal(str(ca))) * 100
        else:
            taux = Decimal('0')

        return {
            'valeur': taux,
            'details': {
                'marge_brute': float(marge),
                'chiffre_affaires': ca,
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_encours_clients(self):
        """Encours clients (factures non payées)"""
        Facture = apps.get_model('facturation', 'Facture')

        queryset = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE', 'EN_RETARD', 'PARTIELLEMENT_PAYEE'],
            montant_restant__gt=0
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        encours = queryset.aggregate(total=Sum('montant_restant'))['total'] or Decimal('0')

        return {
            'valeur': encours,
            'details': {
                'nb_factures_ouvertes': queryset.count(),
                'en_retard': queryset.filter(statut='EN_RETARD').count(),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_delai_paiement_moyen(self):
        """Délai moyen de paiement (DSO)"""
        Facture = apps.get_model('facturation', 'Facture')

        queryset = Facture.objects.filter(
            statut='PAYEE',
            date_paiement_complet__isnull=False,
            date_emission__gte=self.date_debut - timedelta(days=180),
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        # Calculer le délai moyen
        factures_avec_delai = queryset.annotate(
            delai=F('date_paiement_complet') - F('date_emission')
        )

        delais = [f.delai.days for f in factures_avec_delai if f.delai]
        delai_moyen = sum(delais) / len(delais) if delais else 0

        return {
            'valeur': Decimal(str(delai_moyen)),
            'details': {
                'nb_factures_analysees': len(delais),
                'delai_min': min(delais) if delais else 0,
                'delai_max': max(delais) if delais else 0,
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_factures_impayees(self):
        """Nombre de factures impayées"""
        Facture = apps.get_model('facturation', 'Facture')

        queryset = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'RELANCEE', 'EN_RETARD'],
            montant_restant__gt=0
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        return {
            'valeur': Decimal(str(queryset.count())),
            'details': {
                'montant_total': float(queryset.aggregate(Sum('montant_restant'))['montant_restant__sum'] or 0),
                'en_retard': queryset.filter(statut='EN_RETARD').count(),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_taux_recouvrement(self):
        """Taux de recouvrement = Montants encaissés / Montants facturés * 100"""
        Facture = apps.get_model('facturation', 'Facture')

        # Factures émises sur la période
        factures = Facture.objects.filter(
            date_emission__gte=self.date_debut,
            date_emission__lte=self.date_fin,
        )

        if self.mandat:
            factures = factures.filter(mandat=self.mandat)

        montant_facture = factures.aggregate(Sum('montant_ttc'))['montant_ttc__sum'] or Decimal('0')
        montant_paye = factures.aggregate(Sum('montant_paye'))['montant_paye__sum'] or Decimal('0')

        if montant_facture > 0:
            taux = (montant_paye / montant_facture) * 100
        else:
            taux = Decimal('100')

        return {
            'valeur': taux,
            'details': {
                'montant_facture': float(montant_facture),
                'montant_paye': float(montant_paye),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_nb_clients_actifs(self):
        """Nombre de clients avec au moins une facture sur la période"""
        Facture = apps.get_model('facturation', 'Facture')

        queryset = Facture.objects.filter(
            date_emission__gte=self.date_debut,
            date_emission__lte=self.date_fin,
        )

        if self.mandat:
            queryset = queryset.filter(mandat=self.mandat)

        nb_clients = queryset.values('client').distinct().count()

        return {
            'valeur': Decimal(str(nb_clients)),
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_nb_factures_mois(self):
        """Nombre de factures émises dans le mois"""
        factures = self._get_factures()

        return {
            'valeur': Decimal(str(factures.count())),
            'details': {
                'montant_total_ht': float(factures.aggregate(Sum('montant_ht'))['montant_ht__sum'] or 0),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_heures_facturees(self):
        """Heures facturées sur la période"""
        LigneFacture = apps.get_model('facturation', 'LigneFacture')

        queryset = LigneFacture.objects.filter(
            facture__date_emission__gte=self.date_debut,
            facture__date_emission__lte=self.date_fin,
            unite='HEURE'
        )

        if self.mandat:
            queryset = queryset.filter(facture__mandat=self.mandat)

        heures = queryset.aggregate(total=Sum('quantite'))['total'] or Decimal('0')

        return {
            'valeur': heures,
            'details': {
                'nb_lignes': queryset.count(),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_taux_occupation(self):
        """Taux d'occupation des employés"""
        try:
            FicheSalaire = apps.get_model('salaires', 'FicheSalaire')

            queryset = FicheSalaire.objects.filter(
                periode__gte=self.date_debut,
                periode__lte=self.date_fin,
            )

            if self.mandat:
                queryset = queryset.filter(employe__mandat=self.mandat)

            # Moyenne des heures travaillées / heures théoriques
            stats = queryset.aggregate(
                heures_travaillees=Sum('heures_travaillees'),
                jours_travailles=Sum('jours_travailles'),
            )

            heures = stats['heures_travaillees'] or Decimal('0')
            # Supposons 168h/mois théorique
            nb_fiches = queryset.count()
            heures_theoriques = nb_fiches * 168

            if heures_theoriques > 0:
                taux = (heures / heures_theoriques) * 100
            else:
                taux = Decimal('0')

        except Exception:
            taux = Decimal('0')

        return {
            'valeur': taux,
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_masse_salariale(self):
        """Masse salariale brute"""
        try:
            FicheSalaire = apps.get_model('salaires', 'FicheSalaire')

            queryset = FicheSalaire.objects.filter(
                periode__gte=self.date_debut,
                periode__lte=self.date_fin,
                statut__in=['VALIDE', 'PAYE', 'COMPTABILISE']
            )

            if self.mandat:
                queryset = queryset.filter(employe__mandat=self.mandat)

            total = queryset.aggregate(total=Sum('salaire_brut_total'))['total'] or Decimal('0')

        except Exception:
            total = Decimal('0')

        return {
            'valeur': total,
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_charges_sociales(self):
        """Total des charges sociales patronales"""
        try:
            FicheSalaire = apps.get_model('salaires', 'FicheSalaire')

            queryset = FicheSalaire.objects.filter(
                periode__gte=self.date_debut,
                periode__lte=self.date_fin,
                statut__in=['VALIDE', 'PAYE', 'COMPTABILISE']
            )

            if self.mandat:
                queryset = queryset.filter(employe__mandat=self.mandat)

            total = queryset.aggregate(total=Sum('total_charges_patronales'))['total'] or Decimal('0')

        except Exception:
            total = Decimal('0')

        return {
            'valeur': total,
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_tresorerie_nette(self):
        """Trésorerie nette (comptes de liquidités)"""
        try:
            Compte = apps.get_model('comptabilite', 'Compte')

            comptes_tresorerie = Compte.objects.filter(
                numero__startswith='10',  # Comptes de trésorerie
            )

            if self.mandat:
                comptes_tresorerie = comptes_tresorerie.filter(plan_comptable__mandat=self.mandat)

            total = comptes_tresorerie.aggregate(
                solde=Sum('solde_debiteur') - Sum('solde_crediteur')
            )['solde'] or Decimal('0')

        except Exception:
            total = Decimal('0')

        return {
            'valeur': total,
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_ratio_liquidite(self):
        """Ratio de liquidité = Actifs circulants / Dettes court terme"""
        try:
            Compte = apps.get_model('comptabilite', 'Compte')

            # Actifs circulants (comptes 1xxx)
            actifs = Compte.objects.filter(
                numero__regex=r'^1[0-9]',
            )
            if self.mandat:
                actifs = actifs.filter(plan_comptable__mandat=self.mandat)

            total_actifs = actifs.aggregate(
                total=Sum('solde_debiteur') - Sum('solde_crediteur')
            )['total'] or Decimal('0')

            # Dettes court terme (comptes 2xxx)
            passifs = Compte.objects.filter(
                numero__regex=r'^2[0-4]',
            )
            if self.mandat:
                passifs = passifs.filter(plan_comptable__mandat=self.mandat)

            total_passifs = abs(passifs.aggregate(
                total=Sum('solde_crediteur') - Sum('solde_debiteur')
            )['total'] or Decimal('1'))

            ratio = total_actifs / total_passifs if total_passifs else Decimal('0')

        except Exception:
            ratio = Decimal('0')

        return {
            'valeur': ratio,
            'details': {},
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_evolution_ca(self):
        """Évolution du CA par rapport à la période précédente"""
        ca_actuel = self._calcul_ca_mensuel()['valeur']

        # Période précédente
        periode_prec = self.date_debut - relativedelta(months=1)
        calc_prec = KPICalculator(
            mandat=self.mandat,
            date_debut=periode_prec.replace(day=1),
            date_fin=periode_prec
        )
        ca_precedent = calc_prec._calcul_ca_mensuel()['valeur']

        if ca_precedent > 0:
            evolution = ((ca_actuel - ca_precedent) / ca_precedent) * 100
        else:
            evolution = Decimal('0')

        return {
            'valeur': evolution,
            'details': {
                'ca_actuel': float(ca_actuel),
                'ca_precedent': float(ca_precedent),
            },
            'periode_debut': self.date_debut,
            'periode_fin': self.date_fin,
        }

    def _calcul_formule_custom(self, indicateur):
        """Calcule une formule personnalisée"""
        # Contexte pour l'évaluation de la formule
        contexte = {
            'ca_mensuel': float(self._calcul_ca_mensuel()['valeur']),
            'ca_annuel': float(self._calcul_ca_annuel()['valeur']),
            'marge_brute': float(self._calcul_marge_brute()['valeur']),
            'encours_clients': float(self._calcul_encours_clients()['valeur']),
            'masse_salariale': float(self._calcul_masse_salariale()['valeur']),
        }

        try:
            # Évaluation sécurisée de la formule
            resultat = eval(indicateur.formule, {"__builtins__": {}}, contexte)
            return {
                'valeur': Decimal(str(resultat)),
                'details': {'formule': indicateur.formule, 'contexte': contexte},
                'periode_debut': self.date_debut,
                'periode_fin': self.date_fin,
            }
        except Exception as e:
            return {
                'valeur': Decimal('0'),
                'details': {'erreur': str(e)},
                'periode_debut': self.date_debut,
                'periode_fin': self.date_fin,
            }

    def _calcul_depuis_source(self, indicateur):
        """Calcule à partir de la source de données définie"""
        try:
            # Récupérer le modèle source
            app_label, model_name = indicateur.source_table.split('.')
            Model = apps.get_model(app_label, model_name)

            queryset = Model.objects.all()

            # Appliquer les filtres
            if indicateur.filtres_source:
                queryset = queryset.filter(**indicateur.filtres_source)

            # Filtrer par mandat si possible
            if self.mandat and hasattr(Model, 'mandat'):
                queryset = queryset.filter(mandat=self.mandat)

            # Appliquer le type de calcul
            if indicateur.type_calcul == 'SOMME':
                valeur = queryset.aggregate(
                    total=Sum(indicateur.source_champ)
                )['total'] or Decimal('0')
            elif indicateur.type_calcul == 'MOYENNE':
                valeur = queryset.aggregate(
                    moyenne=Avg(indicateur.source_champ)
                )['moyenne'] or Decimal('0')
            elif indicateur.type_calcul == 'COMPTE':
                valeur = Decimal(str(queryset.count()))
            else:
                valeur = Decimal('0')

            return {
                'valeur': valeur,
                'details': {'source': indicateur.source_table},
                'periode_debut': self.date_debut,
                'periode_fin': self.date_fin,
            }

        except Exception as e:
            return {
                'valeur': Decimal('0'),
                'details': {'erreur': str(e)},
                'periode_debut': self.date_debut,
                'periode_fin': self.date_fin,
            }


def calculer_tous_indicateurs(mandat=None, date_debut=None, date_fin=None):
    """
    Calcule tous les indicateurs actifs et enregistre les valeurs.

    Returns:
        list: Liste des ValeurIndicateur créées
    """
    from .models import Indicateur, ValeurIndicateur

    calculator = KPICalculator(mandat, date_debut, date_fin)
    valeurs_creees = []

    for indicateur in Indicateur.objects.filter(actif=True):
        resultat = calculator.calculer_kpi(indicateur)

        # Récupérer la valeur précédente
        valeur_precedente = ValeurIndicateur.objects.filter(
            indicateur=indicateur,
            mandat=mandat,
        ).exclude(
            date_mesure=date_fin or date.today()
        ).order_by('-date_mesure').first()

        # Créer ou mettre à jour la valeur
        valeur, created = ValeurIndicateur.objects.update_or_create(
            indicateur=indicateur,
            mandat=mandat,
            date_mesure=date_fin or date.today(),
            defaults={
                'valeur': resultat['valeur'],
                'valeur_precedente': valeur_precedente.valeur if valeur_precedente else None,
                'periode_debut': resultat.get('periode_debut'),
                'periode_fin': resultat.get('periode_fin'),
                'details_calcul': resultat.get('details', {}),
            }
        )

        # Calculer les variations
        valeur.calculer_variation()
        valeurs_creees.append(valeur)

    return valeurs_creees
