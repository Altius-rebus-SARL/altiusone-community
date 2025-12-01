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
    if created and instance.code_tva and instance.montant_tva > 0:
        from tva.models import OperationTVA, CodeTVA

        code_tva_obj = CodeTVA.objects.filter(code=instance.code_tva).first()
        if code_tva_obj:
            type_op = 'VENTE' if instance.montant_credit > 0 else 'ACHAT'
            montant_base = instance.montant_credit or instance.montant_debit

            OperationTVA.objects.create(
                mandat=instance.mandat,
                ecriture_comptable=instance,
                date_operation=instance.date_ecriture,
                type_operation=type_op,
                montant_ht=montant_base,
                code_tva=code_tva_obj,
                taux_tva=Decimal(instance.code_tva.split('_')[-1]) if '_' in instance.code_tva else Decimal('8.1'),
                montant_tva=instance.montant_tva,
                montant_ttc=montant_base + instance.montant_tva,
                libelle=instance.libelle
            )