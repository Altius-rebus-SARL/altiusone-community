# apps/analytics/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ValeurIndicateur, AlerteMetrique


@receiver(post_save, sender=ValeurIndicateur)
def verifier_alertes(sender, instance, created, **kwargs):
    """Vérifie si des seuils d'alerte sont dépassés"""
    if created:
        indicateur = instance.indicateur

        # Alerte seuil bas
        if indicateur.seuil_alerte_bas and instance.valeur < indicateur.seuil_alerte_bas:
            AlerteMetrique.objects.create(
                indicateur=indicateur,
                valeur_indicateur=instance,
                mandat=instance.mandat,
                niveau='ATTENTION',
                message=f"{indicateur.nom} sous le seuil minimum: {instance.valeur} {indicateur.unite}",
                valeur_detectee=instance.valeur,
                seuil_depasse=indicateur.seuil_alerte_bas
            )

        # Alerte seuil haut
        if indicateur.seuil_alerte_haut and instance.valeur > indicateur.seuil_alerte_haut:
            AlerteMetrique.objects.create(
                indicateur=indicateur,
                valeur_indicateur=instance,
                mandat=instance.mandat,
                niveau='CRITIQUE' if instance.valeur > indicateur.seuil_alerte_haut * 1.2 else 'ATTENTION',
                message=f"{indicateur.nom} dépasse le seuil maximum: {instance.valeur} {indicateur.unite}",
                valeur_detectee=instance.valeur,
                seuil_depasse=indicateur.seuil_alerte_haut
            )