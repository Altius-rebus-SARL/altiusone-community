# apps/core/signals.py
from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver
from decimal import Decimal
import logging
from .models import Client, Mandat, User, AuditLog, Notification

logger = logging.getLogger(__name__)


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

        # Sous-dossiers standards (nom taxe dynamique selon régime du client)
        nom_taxe = 'TVA'
        regime = getattr(instance, 'regime_fiscal_defaut', None)
        if regime:
            nom_taxe = regime.nom_taxe or 'TVA'
        for nom in ['Comptabilité', nom_taxe, 'Salaires', 'Contrats', 'Correspondance']:
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

        # 1. Créer dossier mandat + sous-dossiers module
        dossier = Dossier.objects.create(
            nom=f"Mandat {instance.numero}",
            type_dossier='MANDAT',
            client=instance.client,
            mandat=instance,
            proprietaire=instance.responsable
        )

        # Sous-dossiers par module (nom taxe dynamique selon régime du mandat)
        nom_taxe_mandat = 'TVA'
        if hasattr(instance, 'regime_fiscal') and instance.regime_fiscal_id:
            nom_taxe_mandat = instance.regime_fiscal.nom_taxe or 'TVA'
        for nom_dossier in [
            'Factures', 'Pièces comptables', 'Salaires',
            nom_taxe_mandat, 'Fiscalité', 'Correspondance',
        ]:
            Dossier.objects.create(
                nom=nom_dossier,
                type_dossier='STANDARD',
                parent=dossier,
                client=instance.client,
                mandat=instance,
                proprietaire=instance.responsable
            )

        # 2. Si mandat comptabilité, créer plan comptable
        if instance.type_mandat in ['COMPTA', 'GLOBAL']:
            # Résoudre le type de plan depuis le régime fiscal
            type_plan = None
            if hasattr(instance, 'regime_fiscal') and instance.regime_fiscal_id:
                type_plan = instance.regime_fiscal.type_plan_comptable

            # Trouver le template correspondant au régime fiscal
            if type_plan:
                template = PlanComptable.objects.filter(
                    is_template=True, type_plan=type_plan
                ).first()
            else:
                # Fallback : premier template disponible
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

                # Lier le plan comptable actif au mandat
                instance.plan_comptable_actif = plan
                instance.save(update_fields=['plan_comptable_actif'])

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


@receiver(post_save, sender=Notification)
def envoyer_push_notification(sender, instance, created, **kwargs):
    """Envoie une push notification quand une Notification DB est créée."""
    if not created:
        return

    try:
        from .services.push_notification_service import send_push_to_user, is_push_enabled
        if not is_push_enabled():
            return

        data = {}
        if instance.lien_action:
            data['link'] = instance.lien_action
        if instance.type_notification:
            data['type'] = instance.type_notification

        send_push_to_user(
            user=instance.destinataire,
            title=instance.titre,
            message=instance.message,
            data=data,
        )
    except Exception as e:
        logger.error("Erreur envoi push notification: %s", e)


# =============================================================================
# EMBEDDING SIGNALS (vectorisation automatique)
# =============================================================================

def _on_model_save_generate_embedding(sender, instance, **kwargs):
    """
    Handler post_save générique pour générer un embedding.

    Connecté dynamiquement dans CoreConfig.ready() pour tous les modèles
    listés dans MODEL_EMBEDDING_CONFIG.
    """
    if not hasattr(instance, 'texte_pour_embedding'):
        return

    try:
        from core.tasks import generer_embedding_task
        generer_embedding_task.delay(
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
            object_id=str(instance.pk),
        )
    except Exception as e:
        logger.debug(f"Impossible de lancer la task embedding pour {instance}: {e}")


def register_embedding_signals():
    """
    Connecte le signal post_save pour tous les modèles du registre.

    Appelé depuis CoreConfig.ready().
    """
    from core.embedding_config import MODEL_EMBEDDING_CONFIG, get_model_class

    for app_model in MODEL_EMBEDDING_CONFIG:
        try:
            model_class = get_model_class(app_model)
            post_save.connect(
                _on_model_save_generate_embedding,
                sender=model_class,
                dispatch_uid=f'embedding_{app_model}',
            )
        except Exception as e:
            logger.debug(f"Signal embedding non connecté pour {app_model}: {e}")

