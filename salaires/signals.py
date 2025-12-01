# apps/salaires/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import FicheSalaire, Employe


@receiver(post_save, sender=Employe)
def notifier_nouvel_employe(sender, instance, created, **kwargs):
    """Notifie le gestionnaire de salaires lors d'un nouvel employé"""
    if created:
        from core.models import Notification

        # Trouver les users avec rôle gestionnaire salaires
        gestionnaires = instance.mandat.equipe.filter(
            role__in=['ADMIN', 'MANAGER']
        )

        for user in gestionnaires:
            Notification.objects.create(
                destinataire=user,
                type_notification='INFO',
                titre='Nouvel employé',
                message=f"L'employé {instance.prenom} {instance.nom} a été ajouté.",
                lien_action=f'/salaires/employes/{instance.id}/',
                lien_texte='Voir l\'employé',
                mandat=instance.mandat
            )


@receiver(pre_save, sender=FicheSalaire)
def calculer_fiche_salaire(sender, instance, **kwargs):
    """Calcule automatiquement tous les montants de la fiche de salaire"""
    if not instance.statut == 'VALIDE':  # Ne recalcule pas si déjà validée
        instance.calculer()


@receiver(post_save, sender=FicheSalaire)
def comptabiliser_salaire(sender, instance, **kwargs):
    """Crée l'écriture comptable quand la fiche est validée"""
    if instance.statut == 'VALIDE' and not instance.ecriture_comptable:
        from comptabilite.models import EcritureComptable, Journal, Compte

        journal = Journal.objects.filter(
            mandat=instance.employe.mandat,
            type_journal='OD'
        ).first()

        if journal:
            numero_piece = journal.get_next_numero()

            # Compte de charges salaires
            compte_salaires = Compte.objects.filter(
                plan_comptable__mandat=instance.employe.mandat,
                numero='6000'  # Compte salaires
            ).first()

            # Compte charges sociales
            compte_charges = Compte.objects.filter(
                plan_comptable__mandat=instance.employe.mandat,
                numero='6200'  # Charges sociales
            ).first()

            # Compte personnel (passif)
            compte_personnel = Compte.objects.filter(
                plan_comptable__mandat=instance.employe.mandat,
                numero='2850'  # Compte personnel
            ).first()

            if all([compte_salaires, compte_charges, compte_personnel]):
                # Débit: Charge de salaire brut
                EcritureComptable.objects.create(
                    mandat=instance.employe.mandat,
                    exercice=instance.employe.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=1,
                    date_ecriture=instance.periode,
                    compte=compte_salaires,
                    libelle=f"Salaire {instance.employe.prenom} {instance.employe.nom} - {instance.periode.strftime('%m/%Y')}",
                    montant_debit=instance.salaire_brut_total,
                    statut='VALIDE'
                )

                # Débit: Charges patronales
                EcritureComptable.objects.create(
                    mandat=instance.employe.mandat,
                    exercice=instance.employe.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=2,
                    date_ecriture=instance.periode,
                    compte=compte_charges,
                    libelle=f"Charges sociales {instance.employe.prenom} {instance.employe.nom}",
                    montant_debit=instance.total_charges_patronales,
                    statut='VALIDE'
                )

                # Crédit: Dette envers le personnel (net à payer)
                EcritureComptable.objects.create(
                    mandat=instance.employe.mandat,
                    exercice=instance.employe.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=3,
                    date_ecriture=instance.periode,
                    compte=compte_personnel,
                    libelle=f"Net à payer {instance.employe.prenom} {instance.employe.nom}",
                    montant_credit=instance.salaire_net,
                    statut='VALIDE'
                )



