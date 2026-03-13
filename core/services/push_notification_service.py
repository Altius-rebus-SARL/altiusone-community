# core/services/push_notification_service.py
"""
Service de notifications push (FCM, APNs, Web Push).
Utilise django-push-notifications. Toutes les opérations sont no-op
si PUSH_NOTIFICATIONS_ENABLED est False.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def is_push_enabled():
    """Vérifie si les push notifications sont activées."""
    return getattr(settings, 'PUSH_NOTIFICATIONS_ENABLED', False)


def register_device(user, token, device_type, device_id=None, name=None):
    """
    Enregistre ou met à jour un device pour recevoir des push notifications.

    Args:
        user: instance User Django
        token: registration token (FCM token ou Web Push subscription info)
        device_type: 'android', 'ios', ou 'web'
        device_id: identifiant unique du device (optionnel)
        name: nom lisible du device (optionnel)

    Returns:
        device instance ou None si push désactivé
    """
    if not is_push_enabled():
        logger.debug("Push notifications désactivées — register_device ignoré")
        return None

    try:
        if device_type in ('android', 'ios'):
            from push_notifications.models import GCMDevice
            device, created = GCMDevice.objects.update_or_create(
                registration_id=token,
                defaults={
                    'user': user,
                    'cloud_message_type': 'FCM',
                    'active': True,
                    'device_id': device_id,
                    'name': name or f'{device_type}-{user.username}',
                },
            )
        elif device_type == 'web':
            from push_notifications.models import WebPushDevice
            device, created = WebPushDevice.objects.update_or_create(
                registration_id=token,
                defaults={
                    'user': user,
                    'active': True,
                    'name': name or f'web-{user.username}',
                },
            )
        else:
            logger.warning("Type de device inconnu: %s", device_type)
            return None

        action = "créé" if created else "mis à jour"
        logger.info("Device %s %s pour %s (%s)", device_type, action, user.username, token[:20])
        return device

    except Exception as e:
        logger.error("Erreur register_device: %s", e)
        return None


def unregister_device(user, token):
    """
    Désactive un device pour ne plus recevoir de notifications.

    Args:
        user: instance User Django
        token: registration token à désactiver

    Returns:
        True si désactivé, False sinon
    """
    if not is_push_enabled():
        return False

    try:
        from push_notifications.models import GCMDevice, WebPushDevice

        # Chercher dans les deux types de devices
        updated = GCMDevice.objects.filter(
            user=user, registration_id=token
        ).update(active=False)

        if not updated:
            updated = WebPushDevice.objects.filter(
                user=user, registration_id=token
            ).update(active=False)

        if updated:
            logger.info("Device désactivé pour %s", user.username)
            return True

        logger.warning("Device non trouvé pour %s (token: %s...)", user.username, token[:20])
        return False

    except Exception as e:
        logger.error("Erreur unregister_device: %s", e)
        return False


def send_push_to_user(user, title, message, data=None, badge=None):
    """
    Envoie une notification push à tous les devices actifs d'un utilisateur.

    Args:
        user: instance User Django
        title: titre de la notification
        message: corps du message
        data: dict de données supplémentaires (optionnel)
        badge: nombre à afficher sur l'icône de l'app (optionnel)

    Returns:
        int — nombre de devices notifiés
    """
    if not is_push_enabled():
        return 0

    count = 0
    extra = data or {}

    try:
        from push_notifications.models import GCMDevice, WebPushDevice

        # FCM devices (Android + iOS)
        fcm_devices = GCMDevice.objects.filter(user=user, active=True)
        if fcm_devices.exists():
            try:
                fcm_devices.send_message(
                    title=title,
                    body=message,
                    data=extra,
                    badge=badge,
                )
                count += fcm_devices.count()
            except Exception as e:
                logger.error("Erreur envoi FCM pour %s: %s", user.username, e)

        # Web Push devices
        web_devices = WebPushDevice.objects.filter(user=user, active=True)
        if web_devices.exists():
            try:
                web_devices.send_message(
                    message,
                    extra=extra,
                )
                count += web_devices.count()
            except Exception as e:
                logger.error("Erreur envoi Web Push pour %s: %s", user.username, e)

    except Exception as e:
        logger.error("Erreur send_push_to_user: %s", e)

    return count


def send_push_to_users(users, title, message, data=None):
    """
    Envoie une notification push à plusieurs utilisateurs.

    Args:
        users: queryset ou liste d'instances User
        title: titre de la notification
        message: corps du message
        data: dict de données supplémentaires

    Returns:
        int — nombre total de devices notifiés
    """
    if not is_push_enabled():
        return 0

    total = 0
    for user in users:
        total += send_push_to_user(user, title, message, data)
    return total
