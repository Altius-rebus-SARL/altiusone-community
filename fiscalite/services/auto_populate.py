# fiscalite/services/auto_populate.py
"""Service pour pré-remplir une déclaration fiscale depuis la comptabilité."""
from decimal import Decimal
from django.db.models import Sum


def populate_from_comptabilite(declaration):
    """
    Pré-remplit les montants clés d'une DeclarationFiscale
    depuis les écritures comptables de l'exercice lié.

    PME suisse :
    - Bénéfice = Produits (classes 3-4) - Charges (classes 5-8)
    - Capital propre = Solde comptes classe 28 (fonds propres)
    """
    from comptabilite.models import Compte, EcritureComptable

    exercice = declaration.exercice_comptable
    if not exercice:
        return False

    mandat = declaration.mandat
    plan = mandat.plans_comptables.first()
    if not plan:
        return False

    statuts_valides = ["VALIDE", "LETTRE", "CLOTURE"]

    def _solde_type(type_compte):
        """Calcule le solde net pour un type de compte."""
        comptes = Compte.objects.filter(
            plan_comptable=plan, imputable=True, type_compte=type_compte
        )
        total = Decimal("0")
        for compte in comptes:
            agg = compte.ecritures.filter(
                exercice=exercice, statut__in=statuts_valides
            ).aggregate(
                debit=Sum("montant_debit"),
                credit=Sum("montant_credit"),
            )
            debit = agg["debit"] or Decimal("0")
            credit = agg["credit"] or Decimal("0")
            if type_compte in ("ACTIF", "CHARGE"):
                total += debit - credit
            else:
                total += credit - debit
        return total

    # Bénéfice = Produits - Charges
    produits = _solde_type("PRODUIT")
    charges = _solde_type("CHARGE")
    benefice = produits - charges

    declaration.benefice_avant_impots = benefice
    declaration.benefice_imposable = benefice  # avant corrections fiscales

    # Capital propre = solde des comptes classe 28 (fonds propres PME suisse)
    comptes_fonds_propres = Compte.objects.filter(
        plan_comptable=plan,
        imputable=True,
        numero__startswith="28",
        type_compte="PASSIF",
    )
    capital = Decimal("0")
    for compte in comptes_fonds_propres:
        agg = compte.ecritures.filter(
            exercice=exercice, statut__in=statuts_valides
        ).aggregate(
            debit=Sum("montant_debit"),
            credit=Sum("montant_credit"),
        )
        debit = agg["debit"] or Decimal("0")
        credit = agg["credit"] or Decimal("0")
        capital += credit - debit

    declaration.capital_propre = capital
    declaration.capital_imposable = capital  # avant corrections fiscales

    declaration.save(update_fields=[
        "benefice_avant_impots",
        "benefice_imposable",
        "capital_propre",
        "capital_imposable",
    ])

    return True
