"""
Tâches Celery pour le mailing.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def envoyer_email_task(self, email_id: str):
    """
    Tâche asynchrone pour envoyer un email.

    Args:
        email_id: UUID de l'EmailEnvoye
    """
    from .models import EmailEnvoye
    from .services import EmailService

    try:
        email_envoye = EmailEnvoye.objects.get(id=email_id)

        if email_envoye.statut != EmailEnvoye.Statut.EN_ATTENTE:
            logger.info(f"Email {email_id} déjà traité (statut: {email_envoye.statut})")
            return

        service = EmailService()
        success = service._envoyer_email(email_envoye)

        if not success and email_envoye.tentatives < 3:
            # Retry avec backoff exponentiel
            raise self.retry(countdown=60 * email_envoye.tentatives)

    except EmailEnvoye.DoesNotExist:
        logger.error(f"Email {email_id} non trouvé")
    except Exception as e:
        logger.error(f"Erreur envoi email {email_id}: {e}")
        raise


@shared_task
def analyser_email_task(email_id: str):
    """
    Tâche asynchrone pour analyser un email avec l'IA.

    Args:
        email_id: UUID de l'EmailRecu
    """
    from .models import EmailRecu
    from .services import EmailService

    try:
        email_recu = EmailRecu.objects.get(id=email_id)

        if email_recu.analyse_effectuee:
            logger.info(f"Email {email_id} déjà analysé")
            return

        service = EmailService()
        service.analyser_email(email_recu)

    except EmailRecu.DoesNotExist:
        logger.error(f"Email reçu {email_id} non trouvé")
    except Exception as e:
        logger.error(f"Erreur analyse email {email_id}: {e}")


@shared_task
def fetch_emails_task(configuration_id: str = None):
    """
    Tâche pour récupérer les emails depuis les serveurs IMAP.

    Args:
        configuration_id: UUID de la ConfigurationEmail (optionnel)
    """
    from .models import ConfigurationEmail
    from .services import EmailService

    try:
        if configuration_id:
            configs = ConfigurationEmail.objects.filter(
                id=configuration_id,
                actif=True,
                type_config__in=['IMAP', 'POP3']
            )
        else:
            configs = ConfigurationEmail.objects.filter(
                actif=True,
                type_config__in=['IMAP', 'POP3']
            )

        total_fetched = 0
        for config in configs:
            service = EmailService(configuration=config)
            emails = service.fetch_emails(limit=50, unseen_only=True)
            total_fetched += len(emails)
            logger.info(f"Récupéré {len(emails)} emails depuis {config.nom}")

        return total_fetched

    except Exception as e:
        logger.error(f"Erreur fetch emails: {e}")
        raise


@shared_task
def nettoyer_emails_expires_task():
    """
    Nettoie les emails expirés (emails envoyés en échec après X jours).
    """
    from datetime import timedelta
    from .models import EmailEnvoye

    try:
        # Supprimer les emails en échec de plus de 30 jours
        date_limite = timezone.now() - timedelta(days=30)
        deleted_count, _ = EmailEnvoye.objects.filter(
            statut=EmailEnvoye.Statut.ECHEC,
            created_at__lt=date_limite
        ).delete()

        logger.info(f"Nettoyé {deleted_count} emails en échec")
        return deleted_count

    except Exception as e:
        logger.error(f"Erreur nettoyage emails: {e}")
        raise


@shared_task
def retry_failed_emails_task():
    """
    Relance les emails en échec qui ont moins de 3 tentatives.
    """
    from .models import EmailEnvoye

    try:
        emails_a_relancer = EmailEnvoye.objects.filter(
            statut=EmailEnvoye.Statut.ECHEC,
            tentatives__lt=3
        )

        count = 0
        for email_envoye in emails_a_relancer:
            email_envoye.statut = EmailEnvoye.Statut.EN_ATTENTE
            email_envoye.save(update_fields=['statut'])
            envoyer_email_task.delay(str(email_envoye.id))
            count += 1

        logger.info(f"Relancé {count} emails en échec")
        return count

    except Exception as e:
        logger.error(f"Erreur relance emails: {e}")
        raise
