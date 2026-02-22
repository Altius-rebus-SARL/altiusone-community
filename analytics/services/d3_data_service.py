"""
Service de données pour les visualisations D3.js.

Prépare les données hiérarchiques, relationnelles et temporelles
pour les 6 visualisations D3.js du dashboard analytique.
"""
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from django.apps import apps
from django.db.models import Sum, Count, Q, F, Value, CharField
from django.db.models.functions import TruncDate, TruncMonth, Coalesce


class D3DataService:
    """Service centralisé pour les données D3.js."""

    def __init__(self, mandat=None, annee=None):
        self.mandat = mandat
        self.annee = annee or date.today().year

    # =========================================================================
    # 1. Sunburst - Plan Comptable
    # =========================================================================

    def get_plan_comptable_tree(self):
        """
        Arbre hiérarchique du plan comptable avec soldes agrégés.

        Returns:
            dict: {name, value, children: [{name, value, numero, type_compte, children}]}
        """
        Compte = apps.get_model('comptabilite', 'Compte')
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')

        # Filtrer les comptes du mandat
        comptes_qs = Compte.objects.all()
        ecritures_qs = EcritureComptable.objects.filter(
            date_ecriture__year=self.annee,
            statut__in=['VALIDE', 'LETTRE', 'CLOTURE'],
        )
        if self.mandat:
            comptes_qs = comptes_qs.filter(plan_comptable__mandat=self.mandat)
            ecritures_qs = ecritures_qs.filter(mandat=self.mandat)

        # Soldes par compte
        soldes = {}
        for row in ecritures_qs.values('compte_id').annotate(
            total_debit=Coalesce(Sum('montant_debit'), Decimal('0')),
            total_credit=Coalesce(Sum('montant_credit'), Decimal('0')),
        ):
            solde = abs(float(row['total_debit'] - row['total_credit']))
            soldes[row['compte_id']] = solde

        # Indexer les comptes
        comptes = list(comptes_qs.values(
            'id', 'numero', 'libelle', 'type_compte', 'classe', 'niveau', 'compte_parent_id'
        ))
        by_parent = defaultdict(list)
        for c in comptes:
            by_parent[c['compte_parent_id']].append(c)

        def build_node(compte):
            children = by_parent.get(compte['id'], [])
            if children:
                child_nodes = [build_node(ch) for ch in sorted(children, key=lambda x: x['numero'])]
                child_nodes = [cn for cn in child_nodes if cn['value'] > 0]
                total = sum(cn['value'] for cn in child_nodes)
                return {
                    'name': f"{compte['numero']} {compte['libelle']}",
                    'numero': compte['numero'],
                    'type_compte': compte['type_compte'],
                    'value': total,
                    'children': child_nodes,
                }
            else:
                return {
                    'name': f"{compte['numero']} {compte['libelle']}",
                    'numero': compte['numero'],
                    'type_compte': compte['type_compte'],
                    'value': soldes.get(compte['id'], 0),
                }

        # Construire l'arbre depuis les racines
        roots = by_parent.get(None, [])
        if not roots:
            return {'name': 'Plan comptable', 'value': 0, 'children': []}

        root_nodes = [build_node(r) for r in sorted(roots, key=lambda x: x['numero'])]
        root_nodes = [rn for rn in root_nodes if rn['value'] > 0]
        total = sum(rn['value'] for rn in root_nodes)

        return {
            'name': 'Plan comptable',
            'value': total,
            'children': root_nodes,
        }

    # =========================================================================
    # 2. Sankey - Flux Trésorerie
    # =========================================================================

    def get_flux_tresorerie(self):
        """
        Données Sankey pour les flux de trésorerie.

        Returns:
            dict: {nodes: [{id, name, color}], links: [{source, target, value}]}
        """
        Facture = apps.get_model('facturation', 'Facture')
        LigneFacture = apps.get_model('facturation', 'LigneFacture')
        FicheSalaire = apps.get_model('salaires', 'FicheSalaire')
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')

        nodes = []
        links = []
        node_map = {}

        def add_node(node_id, name, color=None):
            if node_id not in node_map:
                node_map[node_id] = len(nodes)
                nodes.append({'id': node_id, 'name': name, 'color': color})
            return node_map[node_id]

        # --- Sources (revenus par type de prestation) ---
        factures_qs = Facture.objects.filter(
            date_emission__year=self.annee,
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
        )
        if self.mandat:
            factures_qs = factures_qs.filter(mandat=self.mandat)

        lignes_qs = LigneFacture.objects.filter(
            facture__in=factures_qs,
            prestation__isnull=False,
        ).values(
            'prestation__type_prestation__code',
            'prestation__type_prestation__libelle',
        ).annotate(total=Sum('montant_ht'))

        # Noeud central "Revenus"
        revenus_idx = add_node('revenus', 'Revenus', '#10b981')

        for row in lignes_qs:
            tp_code = row['prestation__type_prestation__code'] or 'AUTRE'
            tp_label = row['prestation__type_prestation__libelle'] or tp_code.replace('_', ' ').title()
            val = float(row['total'] or 0)
            if val > 0:
                src_idx = add_node(f'src_{tp_code}', tp_label, '#3b82f6')
                links.append({'source': src_idx, 'target': revenus_idx, 'value': val})

        # Revenus sans prestation
        revenus_sans_presta = float(
            LigneFacture.objects.filter(
                facture__in=factures_qs,
                prestation__isnull=True,
            ).aggregate(total=Sum('montant_ht'))['total'] or 0
        )
        if revenus_sans_presta > 0:
            src_idx = add_node('src_divers', 'Divers', '#6b7280')
            links.append({'source': src_idx, 'target': revenus_idx, 'value': revenus_sans_presta})

        # --- Destinations (dépenses) ---
        # Salaires
        fiches_qs = FicheSalaire.objects.filter(
            annee=self.annee,
            statut__in=['VALIDE', 'PAYE', 'COMPTABILISE'],
        )
        if self.mandat:
            fiches_qs = fiches_qs.filter(employe__mandat=self.mandat)

        masse_salariale = fiches_qs.aggregate(
            brut=Coalesce(Sum('salaire_brut_total'), Decimal('0')),
            avs=Coalesce(Sum(F('avs_employe') + F('avs_employeur')), Decimal('0')),
            lpp=Coalesce(Sum(F('lpp_employe') + F('lpp_employeur')), Decimal('0')),
            laa=Coalesce(Sum(F('laa_employe') + F('laa_employeur')), Decimal('0')),
            ac=Coalesce(Sum(F('ac_employe') + F('ac_employeur')), Decimal('0')),
            impot=Coalesce(Sum('impot_source'), Decimal('0')),
        )

        salaires_net = float(fiches_qs.aggregate(
            total=Coalesce(Sum('salaire_net'), Decimal('0'))
        )['total'])

        if salaires_net > 0:
            dest_sal = add_node('dest_salaires', 'Salaires nets', '#f59e0b')
            links.append({'source': revenus_idx, 'target': dest_sal, 'value': salaires_net})

        cotisations_total = float(masse_salariale['avs'] + masse_salariale['lpp'] +
                                  masse_salariale['laa'] + masse_salariale['ac'])
        if cotisations_total > 0:
            dest_cot = add_node('dest_cotisations', 'Cotisations sociales', '#ef4444')
            links.append({'source': revenus_idx, 'target': dest_cot, 'value': cotisations_total})

        impot = float(masse_salariale['impot'])
        if impot > 0:
            dest_impot = add_node('dest_impot', 'Impôt source', '#8b5cf6')
            links.append({'source': revenus_idx, 'target': dest_impot, 'value': impot})

        # Charges comptables (4xxx = charges)
        ecritures_charges = EcritureComptable.objects.filter(
            date_ecriture__year=self.annee,
            statut__in=['VALIDE', 'LETTRE', 'CLOTURE'],
            compte__classe=4,
        ).exclude(
            # Exclure salaires déjà comptés
            compte__numero__startswith='42',
        )
        if self.mandat:
            ecritures_charges = ecritures_charges.filter(mandat=self.mandat)

        charges_fournisseurs = float(
            ecritures_charges.aggregate(
                total=Coalesce(Sum('montant_debit'), Decimal('0'))
            )['total']
        )
        if charges_fournisseurs > 0:
            dest_fourn = add_node('dest_fournisseurs', 'Charges exploitation', '#f97316')
            links.append({'source': revenus_idx, 'target': dest_fourn, 'value': charges_fournisseurs})

        # TVA nette
        try:
            DeclarationTVA = apps.get_model('tva', 'DeclarationTVA')
            tva_due = float(DeclarationTVA.objects.filter(
                periode_debut__year=self.annee,
            ).aggregate(
                total=Coalesce(Sum('tva_due_total'), Decimal('0'))
            )['total'])
            if tva_due > 0:
                dest_tva = add_node('dest_tva', 'TVA due', '#06b6d4')
                links.append({'source': revenus_idx, 'target': dest_tva, 'value': tva_due})
        except LookupError:
            pass

        # Filtrer les liens avec value > 0
        links = [l for l in links if l['value'] > 0]

        return {'nodes': nodes, 'links': links}

    # =========================================================================
    # 3. Calendar Heatmap - Activité
    # =========================================================================

    def get_calendrier_activite(self, metric='factures'):
        """
        Données calendrier heatmap par jour.

        Args:
            metric: 'factures', 'heures', 'paiements'

        Returns:
            dict: {dates: {"2026-01-15": {count, montant}}, metric, annee,
                   stats: {min, max, total, jours_actifs}}
        """
        dates = {}

        if metric == 'factures':
            Facture = apps.get_model('facturation', 'Facture')
            qs = Facture.objects.filter(
                date_emission__year=self.annee,
                statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
            )
            if self.mandat:
                qs = qs.filter(mandat=self.mandat)
            for row in qs.annotate(
                jour=TruncDate('date_emission')
            ).values('jour').annotate(
                count=Count('id'),
                montant=Coalesce(Sum('montant_ht'), Decimal('0')),
            ):
                key = row['jour'].isoformat()
                dates[key] = {'count': row['count'], 'montant': float(row['montant'])}

        elif metric == 'heures':
            TimeTracking = apps.get_model('facturation', 'TimeTracking')
            qs = TimeTracking.objects.filter(date_travail__year=self.annee)
            if self.mandat:
                qs = qs.filter(mandat=self.mandat)
            for row in qs.values('date_travail').annotate(
                count=Count('id'),
                montant=Coalesce(Sum('duree_minutes'), 0),
            ):
                key = row['date_travail'].isoformat()
                heures = round(row['montant'] / 60, 1)
                dates[key] = {'count': row['count'], 'montant': heures}

        elif metric == 'paiements':
            Paiement = apps.get_model('facturation', 'Paiement')
            qs = Paiement.objects.filter(
                date_paiement__year=self.annee,
                valide=True,
            )
            if self.mandat:
                qs = qs.filter(facture__mandat=self.mandat)
            for row in qs.annotate(
                jour=TruncDate('date_paiement')
            ).values('jour').annotate(
                count=Count('id'),
                montant=Coalesce(Sum('montant'), Decimal('0')),
            ):
                key = row['jour'].isoformat()
                dates[key] = {'count': row['count'], 'montant': float(row['montant'])}

        # Statistiques
        values = [d['montant'] for d in dates.values()] if dates else [0]
        stats = {
            'min': min(values),
            'max': max(values),
            'total': sum(values),
            'jours_actifs': len(dates),
        }

        return {
            'dates': dates,
            'metric': metric,
            'annee': self.annee,
            'stats': stats,
        }

    # =========================================================================
    # 4. Force-directed Network - Écosystème Clients
    # =========================================================================

    def get_reseau_clients(self):
        """
        Données réseau clients/mandats/prestations.

        Returns:
            dict: {nodes: [{id, name, type, value, ...}], links: [{source, target, value, type}]}
        """
        Client = apps.get_model('core', 'Client')
        Mandat = apps.get_model('core', 'Mandat')
        Facture = apps.get_model('facturation', 'Facture')

        nodes = []
        links = []
        node_ids = set()

        # Clients avec CA
        clients_qs = Client.objects.filter(
            statut='ACTIF',
            factures__date_emission__year=self.annee,
            factures__statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
        ).distinct().annotate(
            ca_total=Coalesce(Sum(
                'factures__montant_ht',
                filter=Q(
                    factures__date_emission__year=self.annee,
                    factures__statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
                )
            ), Decimal('0')),
        )

        if self.mandat:
            clients_qs = clients_qs.filter(mandats=self.mandat)

        for client in clients_qs[:50]:  # Limiter pour lisibilité
            node_id = f'client_{client.pk}'
            nodes.append({
                'id': node_id,
                'name': client.raison_sociale,
                'type': 'client',
                'value': float(client.ca_total),
            })
            node_ids.add(node_id)

        # Mandats liés
        client_pks = [c.pk for c in clients_qs[:50]]
        mandats_qs = Mandat.objects.filter(
            client_id__in=client_pks,
            statut='ACTIF',
        ).select_related('client')

        for mandat in mandats_qs:
            node_id = f'mandat_{mandat.pk}'
            if node_id not in node_ids:
                ca_mandat = float(Facture.objects.filter(
                    mandat=mandat,
                    date_emission__year=self.annee,
                    statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE'],
                ).aggregate(total=Coalesce(Sum('montant_ht'), Decimal('0')))['total'])

                nodes.append({
                    'id': node_id,
                    'name': f"{mandat.numero}",
                    'type': 'mandat',
                    'type_mandat': mandat.type_mandat,
                    'value': ca_mandat,
                })
                node_ids.add(node_id)

            client_node = f'client_{mandat.client_id}'
            if client_node in node_ids:
                links.append({
                    'source': client_node,
                    'target': node_id,
                    'type': mandat.type_mandat,
                    'value': 1,
                })

        return {'nodes': nodes, 'links': links}

    # =========================================================================
    # 5. Icicle - Décomposition Salaires
    # =========================================================================

    def get_decomposition_salaires(self, mois=None):
        """
        Arbre hiérarchique de la masse salariale.

        Args:
            mois: Mois spécifique (1-12) ou None pour l'année complète.

        Returns:
            dict: {name, value, children: [{name (employe), value, children: [{composante, value}]}]}
        """
        FicheSalaire = apps.get_model('salaires', 'FicheSalaire')

        qs = FicheSalaire.objects.filter(
            annee=self.annee,
            statut__in=['VALIDE', 'PAYE', 'COMPTABILISE'],
        ).select_related('employe')
        if mois:
            qs = qs.filter(mois=mois)
        if self.mandat:
            qs = qs.filter(employe__mandat=self.mandat)

        employes_data = defaultdict(lambda: defaultdict(float))
        for fiche in qs:
            emp_key = f"{fiche.employe.prenom} {fiche.employe.nom}"
            employes_data[emp_key]['Salaire brut'] += float(fiche.salaire_brut_total)
            employes_data[emp_key]['AVS'] += float(fiche.avs_employe + fiche.avs_employeur)
            employes_data[emp_key]['LPP'] += float(fiche.lpp_employe + fiche.lpp_employeur)
            employes_data[emp_key]['LAA'] += float(fiche.laa_employe + fiche.laa_employeur)
            employes_data[emp_key]['AC'] += float(fiche.ac_employe + fiche.ac_employeur)
            employes_data[emp_key]['Impôt source'] += float(fiche.impot_source)
            employes_data[emp_key]['Allocations'] += float(
                fiche.allocations_familiales + fiche.autres_allocations
            )
            employes_data[emp_key]['Salaire net'] += float(fiche.salaire_net)

        children = []
        for emp_name, composantes in sorted(employes_data.items()):
            emp_children = []
            for comp_name, comp_val in composantes.items():
                if comp_val > 0:
                    emp_children.append({'name': comp_name, 'value': round(comp_val, 2)})
            if emp_children:
                emp_total = sum(c['value'] for c in emp_children)
                children.append({
                    'name': emp_name,
                    'value': round(emp_total, 2),
                    'children': emp_children,
                })

        total = sum(c['value'] for c in children)
        label = f"Masse salariale {self.annee}"
        if mois:
            mois_labels = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                           'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            label = f"Salaires {mois_labels[mois]} {self.annee}"

        return {
            'name': label,
            'value': round(total, 2),
            'children': children,
        }

    # =========================================================================
    # 6. Timeline Gantt - Projets & Opérations
    # =========================================================================

    def get_timeline_projets(self, mandat_id=None):
        """
        Données timeline/Gantt pour les projets.

        Returns:
            dict: {projets: [{nom, date_debut, date_fin, operations: [{...}]}],
                   date_min, date_max}
        """
        Position = apps.get_model('projets', 'Position')
        Operation = apps.get_model('projets', 'Operation')

        positions_qs = Position.objects.filter(
            statut__in=['PLANIFIE', 'EN_COURS'],
        ).select_related('mandat', 'mandat__client')

        if self.mandat:
            positions_qs = positions_qs.filter(mandat=self.mandat)
        elif mandat_id:
            positions_qs = positions_qs.filter(mandat_id=mandat_id)

        projets = []
        all_dates = []

        for pos in positions_qs.prefetch_related('operations')[:30]:
            ops = []
            for op in pos.operations.exclude(statut='ANNULEE').order_by('ordre'):
                op_data = {
                    'id': str(op.pk),
                    'titre': op.titre,
                    'date_debut': op.date_debut.isoformat() if op.date_debut else None,
                    'date_fin': op.date_fin.isoformat() if op.date_fin else None,
                    'statut': op.statut,
                    'priorite': op.priorite,
                }
                ops.append(op_data)
                if op.date_debut:
                    all_dates.append(op.date_debut)
                if op.date_fin:
                    all_dates.append(op.date_fin)

            projet_data = {
                'id': str(pos.pk),
                'nom': f"{pos.mandat.client.raison_sociale} - {pos.titre}" if pos.mandat else pos.titre,
                'numero': pos.numero,
                'date_debut': pos.date_debut.isoformat() if pos.date_debut else None,
                'date_fin': pos.date_fin.isoformat() if pos.date_fin else None,
                'statut': pos.statut,
                'operations': ops,
            }
            projets.append(projet_data)
            if pos.date_debut:
                all_dates.append(pos.date_debut)
            if pos.date_fin:
                all_dates.append(pos.date_fin)

        date_min = min(all_dates).isoformat() if all_dates else date(self.annee, 1, 1).isoformat()
        date_max = max(all_dates).isoformat() if all_dates else date(self.annee, 12, 31).isoformat()

        return {
            'projets': projets,
            'date_min': date_min,
            'date_max': date_max,
        }
