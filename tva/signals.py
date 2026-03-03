# apps/tva/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import DeclarationTVA, LigneTVA, OperationTVA, CorrectionTVA


@receiver(post_save, sender=LigneTVA)
@receiver(post_delete, sender=LigneTVA)
def recalculer_declaration_ligne(sender, instance, **kwargs):
    """Recalcule les totaux quand une ligne change"""
    instance.declaration.recalculer_totaux()


@receiver(post_save, sender=CorrectionTVA)
@receiver(post_delete, sender=CorrectionTVA)
def recalculer_declaration_correction(sender, instance, **kwargs):
    """Recalcule les totaux quand une correction change"""
    instance.declaration.recalculer_totaux()


@receiver(post_save, sender=DeclarationTVA)
def notification_declaration_validee(sender, instance, created, **kwargs):
    """Notifie quand une déclaration est validée"""
    if instance.statut == "VALIDE" and not created:
        from core.models import Notification

        # Notifier le responsable et l'équipe
        destinataires = [instance.mandat.responsable]
        if instance.mandat.equipe.exists():
            destinataires.extend(instance.mandat.equipe.all())

        for user in destinataires:
            Notification.objects.create(
                destinataire=user,
                type_notification="INFO",
                titre="Déclaration TVA validée",
                message=f"La déclaration {instance.numero_declaration} est prête.",
                lien_action=f"/tva/declarations/{instance.id}/",
                mandat=instance.mandat,
            )

# # apps/tva/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import DeclarationTVA, LigneTVA, OperationTVA


# @receiver(post_save, sender=LigneTVA)
# def recalculer_declaration_tva(sender, instance, **kwargs):
#     """Recalcule les totaux de la déclaration après ajout/modif ligne"""
#     declaration = instance.declaration

#     lignes = declaration.lignes.all()

#     # Totaux par catégorie
#     declaration.tva_due_total = sum(
#         l.montant_tva for l in lignes
#         if l.code_tva.categorie == 'TVA_DUE'
#     )

#     declaration.tva_prealable_total = sum(
#         l.montant_tva for l in lignes
#         if l.code_tva.categorie == 'TVA_PREALABLE'
#     )

#     declaration.calculer_solde()


# @receiver(post_save, sender=DeclarationTVA)
# def notifier_echeance_tva(sender, instance, created, **kwargs):
#     """Notifie l'équipe quand une déclaration TVA est validée"""
#     if instance.statut == 'VALIDE' and not created:
#         from core.models import Notification

#         for user in instance.mandat.equipe.all():
#             Notification.objects.create(
#                 destinataire=user,
#                 type_notification='SUCCESS',
#                 titre='Déclaration TVA validée',
#                 message=f"La déclaration TVA {instance.numero_declaration} est prête à être soumise.",
#                 lien_action=f'/tva/declarations/{instance.id}/',
#                 lien_texte='Voir la déclaration',
#                 mandat=instance.mandat
#             )


