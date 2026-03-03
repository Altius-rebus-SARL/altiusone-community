# apps/core/signals.py
from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver
from decimal import Decimal
from .models import Client, Mandat, User, AuditLog, Notification


@receiver(post_save, sender=Client)
def creer_dossier_client(sender, instance, created, **kwargs):
    """Crée automatiquement l'arborescence de dossiers pour un nouveau client"""
    if created:
        from documents.models import Dossier

        # Dossier racine client
        dossier_client = Dossier.objects.create(
            nom=instance.raison_sociale,
            type_dossier='CLIENT',
            client=instance,
            proprietaire=instance.responsable
        )

        # Sous-dossiers standards
        for nom in ['Comptabilité', 'TVA', 'Salaires', 'Contrats', 'Correspondance']:
            Dossier.objects.create(
                nom=nom,
                type_dossier='STANDARD',
                parent=dossier_client,
                client=instance,
                proprietaire=instance.responsable
            )


@receiver(post_save, sender=Mandat)
def initialiser_mandat(sender, instance, created, **kwargs):
    """Initialise un nouveau mandat avec sa configuration"""
    if created:
        from documents.models import Dossier
        from comptabilite.models import PlanComptable, Journal

        # 1. Créer dossier mandat
        dossier = Dossier.objects.create(
            nom=f"Mandat {instance.numero}",
            type_dossier='MANDAT',
            client=instance.client,
            mandat=instance,
            proprietaire=instance.responsable
        )

        # 2. Si mandat comptabilité, créer plan comptable
        if instance.type_mandat in ['COMPTA', 'GLOBAL']:
            # Copier plan comptable template
            template = PlanComptable.objects.filter(is_template=True).first()
            if template:
                plan = PlanComptable.objects.create(
                    nom=f"Plan comptable {instance.client.raison_sociale}",
                    type_plan=template.type_plan,
                    mandat=instance,
                    base_sur=template
                )

                # Copier les comptes du template
                from comptabilite.models import Compte
                for compte_template in template.comptes.all():
                    Compte.objects.create(
                        plan_comptable=plan,
                        numero=compte_template.numero,
                        libelle=compte_template.libelle,
                        type_compte=compte_template.type_compte,
                        classe=compte_template.classe,
                        niveau=compte_template.niveau,
                        imputable=compte_template.imputable,
                        lettrable=compte_template.lettrable
                    )

                # Créer journaux standards
                journaux = [
                    ('VTE', 'Ventes', 'VTE'),
                    ('ACH', 'Achats', 'ACH'),
                    ('BNQ', 'Banque', 'BNQ'),
                    ('CAS', 'Caisse', 'CAS'),
                    ('OD', 'Opérations diverses', 'OD'),
                ]

                for code, libelle, type_j in journaux:
                    Journal.objects.create(
                        mandat=instance,
                        code=code,
                        libelle=libelle,
                        type_journal=type_j,
                        prefixe_piece=code
                    )

        # 3. Si mandat TVA, créer config TVA
        if instance.type_mandat in ['TVA', 'COMPTA', 'GLOBAL']:
            from tva.models import ConfigurationTVA
            ConfigurationTVA.objects.create(
                mandat=instance,
                numero_tva=instance.client.tva_number,
                assujetti_tva=bool(instance.client.tva_number)
            )

        # 4. Notification au responsable
        Notification.objects.create(
            destinataire=instance.responsable,
            type_notification='INFO',
            titre='Nouveau mandat créé',
            message=f"Le mandat {instance.numero} pour {instance.client.raison_sociale} a été créé.",
            lien_action=f'/mandats/{instance.id}/',
            lien_texte='Voir le mandat',
            mandat=instance
        )








