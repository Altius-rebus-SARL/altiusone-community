# apps/comptabilite/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import EcritureComptable, Compte, PieceComptable
from decimal import Decimal


@receiver(pre_save, sender=EcritureComptable)
def valider_ecriture(sender, instance, **kwargs):
    """Validation avant sauvegarde d'une écriture"""
    from django.core.exceptions import ValidationError

    # Une écriture doit être soit au débit, soit au crédit
    if instance.montant_debit > 0 and instance.montant_credit > 0:
        raise ValidationError("Une écriture ne peut pas avoir débit ET crédit")

    if instance.montant_debit == 0 and instance.montant_credit == 0:
        raise ValidationError("Une écriture doit avoir un montant")


@receiver(post_save, sender=EcritureComptable)
def mettre_a_jour_soldes(sender, instance, created, **kwargs):
    """Met à jour les soldes des comptes après une écriture"""
    if instance.statut == 'VALIDE':
        compte = instance.compte

        # Recalculer les soldes
        ecritures_validees = EcritureComptable.objects.filter(
            compte=compte,
            statut__in=['VALIDE', 'LETTRE', 'CLOTURE']
        )

        compte.solde_debit = sum(e.montant_debit for e in ecritures_validees)
        compte.solde_credit = sum(e.montant_credit for e in ecritures_validees)
        compte.save(update_fields=['solde_debit', 'solde_credit'])


@receiver(post_save, sender=EcritureComptable)
def verifier_equilibre_piece(sender, instance, **kwargs):
    """Vérifie l'équilibre de la pièce comptable"""
    if instance.numero_piece:
        piece, created = PieceComptable.objects.get_or_create(
            mandat=instance.mandat,
            numero_piece=instance.numero_piece,
            defaults={
                'journal': instance.journal,
                'date_piece': instance.date_ecriture,
                'libelle': instance.libelle,
                'statut': 'BROUILLON'
            }
        )
        piece.calculer_equilibre()


@receiver(post_save, sender=EcritureComptable)
def creer_operation_tva(sender, instance, created, **kwargs):
    """Crée automatiquement une opération TVA si code TVA présent"""
    if not (created and instance.code_tva and instance.montant_tva and instance.montant_tva > 0):
        return

    from tva.models import OperationTVA, CodeTVA

    # Eviter les doublons
    if OperationTVA.objects.filter(ecriture_comptable=instance).exists():
        return

    code_tva_obj = CodeTVA.objects.filter(code=instance.code_tva).first()
    if not code_tva_obj:
        return

    type_op = 'VENTE' if instance.montant_credit > 0 else 'ACHAT'
    montant_base = instance.montant_credit or instance.montant_debit

    # Résoudre le taux TVA depuis le CodeTVA ou le montant
    taux = Decimal('0')
    if code_tva_obj.taux_applicable:
        taux = code_tva_obj.taux_applicable.taux
    elif montant_base > 0:
        # Calculer le taux implicite
        taux = (instance.montant_tva / montant_base * 100).quantize(Decimal('0.01'))

    OperationTVA.objects.create(
        mandat=instance.mandat,
        ecriture_comptable=instance,
        date_operation=instance.date_ecriture,
        type_operation=type_op,
        montant_ht=montant_base,
        code_tva=code_tva_obj,
        taux_tva=taux,
        montant_tva=instance.montant_tva,
        montant_ttc=montant_base + instance.montant_tva,
        libelle=instance.libelle
    )