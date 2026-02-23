"""
Service de notification pour les tâches.
"""
import logging
from typing import Optional, List

from django.contrib.auth import get_user_model
from django.urls import reverse

from mailing.services import EmailService

User = get_user_model()
logger = logging.getLogger(__name__)


def envoyer_notification_assignation(tache, assigne_par, only_users=None):
    """
    Envoie une notification email aux assignés d'une tâche.

    Args:
        tache: Instance de Tache (avec assignes M2M déjà sauvegardés)
        assigne_par: User qui a assigné la tâche
        only_users: Liste optionnelle d'utilisateurs à notifier (si None, notifie tous les assignés)
    """
    service = EmailService()

    users_to_notify = only_users if only_users else tache.assignes.all()

    for user in users_to_notify:
        if not user.email:
            logger.warning(f"Pas d'email pour {user.username}, notification ignorée")
            continue

        # Ne pas notifier celui qui assigne si c'est lui-même
        if user == assigne_par:
            continue

        context = {
            'destinataire_prenom': user.first_name or user.username,
            'titre_tache': tache.titre,
            'description_tache': tache.description or '',
            'priorite': tache.get_priorite_display(),
            'date_echeance': tache.date_echeance.strftime('%d.%m.%Y') if tache.date_echeance else '-',
            'mandat': str(tache.mandat) if tache.mandat else '-',
            'prestation': str(tache.prestation) if tache.prestation else '-',
            'assigne_par': assigne_par.get_full_name() or assigne_par.username,
            'lien_tache': reverse('core:tache-detail', kwargs={'pk': str(tache.pk)}),
        }

        try:
            service.send_template_email(
                destinataire=user.email,
                template_code='TACHE_ASSIGNATION',
                context=context,
                utilisateur=assigne_par,
                mandat=tache.mandat,
                content_type='tache',
                object_id=str(tache.pk),
            )
            logger.info(f"Notification tâche envoyée à {user.email} pour '{tache.titre}'")
        except Exception as e:
            logger.error(f"Erreur envoi notification tâche à {user.email}: {e}")
