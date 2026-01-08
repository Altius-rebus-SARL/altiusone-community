"""
Services pour la gestion des emails.
"""
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from django.conf import settings
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template import Template, Context
from django.utils import timezone

from .models import ConfigurationEmail, TemplateEmail, EmailEnvoye, EmailRecu

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service pour l'envoi et la réception d'emails.

    Fonctionnalités:
    - Envoi d'emails via SMTP (configuration en base de données)
    - Envoi d'emails basés sur des templates
    - Réception d'emails via IMAP/POP3
    - Test de configuration
    """

    def __init__(self, configuration: Optional[ConfigurationEmail] = None):
        """
        Initialise le service avec une configuration spécifique ou par défaut.

        Args:
            configuration: Configuration email à utiliser (optionnel)
        """
        self.configuration = configuration

    def get_configuration(self, usage: str = 'NOREPLY') -> Optional[ConfigurationEmail]:
        """
        Récupère la configuration par défaut pour un usage donné.
        """
        if self.configuration:
            return self.configuration
        return ConfigurationEmail.get_default(usage)

    def send_email(
        self,
        destinataire: str,
        sujet: str,
        corps_html: str,
        corps_texte: str = '',
        cc: List[str] = None,
        bcc: List[str] = None,
        pieces_jointes: List[Dict] = None,
        configuration: ConfigurationEmail = None,
        utilisateur=None,
        mandat=None,
        content_type: str = '',
        object_id: str = '',
        async_send: bool = True
    ) -> EmailEnvoye:
        """
        Envoie un email.

        Args:
            destinataire: Adresse email du destinataire
            sujet: Sujet de l'email
            corps_html: Contenu HTML
            corps_texte: Contenu texte brut (optionnel)
            cc: Liste des adresses en copie
            bcc: Liste des adresses en copie cachée
            pieces_jointes: Liste de pièces jointes [{"nom": "doc.pdf", "path": "/path/to/file"}]
            configuration: Configuration SMTP à utiliser
            utilisateur: Utilisateur qui envoie l'email
            mandat: Mandat associé
            content_type: Type de contenu (ex: "facture", "invitation")
            object_id: ID de l'objet associé
            async_send: Si True, envoie via Celery (par défaut)

        Returns:
            EmailEnvoye: L'enregistrement de l'email
        """
        config = configuration or self.get_configuration('NOREPLY')

        # Créer l'enregistrement
        email_envoye = EmailEnvoye.objects.create(
            configuration=config,
            destinataire=destinataire,
            destinataires_cc=cc or [],
            destinataires_bcc=bcc or [],
            sujet=sujet,
            corps_html=corps_html,
            corps_texte=corps_texte or '',
            pieces_jointes=pieces_jointes or [],
            statut=EmailEnvoye.Statut.EN_ATTENTE,
            utilisateur=utilisateur,
            mandat=mandat,
            content_type=content_type,
            object_id=object_id
        )

        if async_send:
            # Envoi asynchrone via Celery
            from .tasks import envoyer_email_task
            envoyer_email_task.delay(str(email_envoye.id))
        else:
            # Envoi synchrone
            self._envoyer_email(email_envoye)

        return email_envoye

    def send_template_email(
        self,
        destinataire: str,
        template_code: str,
        context: Dict,
        cc: List[str] = None,
        bcc: List[str] = None,
        pieces_jointes: List[Dict] = None,
        utilisateur=None,
        mandat=None,
        content_type: str = '',
        object_id: str = '',
        async_send: bool = True
    ) -> Optional[EmailEnvoye]:
        """
        Envoie un email basé sur un template.

        Args:
            destinataire: Adresse email du destinataire
            template_code: Code du template (ex: "INVITATION_STAFF")
            context: Dictionnaire de variables pour le template
            ... autres paramètres identiques à send_email

        Returns:
            EmailEnvoye ou None si le template n'existe pas
        """
        try:
            template = TemplateEmail.objects.get(code=template_code, actif=True)
        except TemplateEmail.DoesNotExist:
            logger.error(f"Template email '{template_code}' non trouvé")
            return None

        # Rendre le template
        sujet, corps_html, corps_texte = template.render(context)

        return self.send_email(
            destinataire=destinataire,
            sujet=sujet,
            corps_html=corps_html,
            corps_texte=corps_texte,
            cc=cc,
            bcc=bcc,
            pieces_jointes=pieces_jointes,
            configuration=template.configuration,
            utilisateur=utilisateur,
            mandat=mandat,
            content_type=content_type or template.type_template,
            object_id=object_id,
            async_send=async_send
        )

    def _envoyer_email(self, email_envoye: EmailEnvoye) -> bool:
        """
        Effectue l'envoi réel de l'email.

        Args:
            email_envoye: L'enregistrement EmailEnvoye à envoyer

        Returns:
            bool: True si l'envoi a réussi
        """
        config = email_envoye.configuration

        try:
            email_envoye.tentatives += 1
            email_envoye.save(update_fields=['tentatives'])

            # Préparer la connexion SMTP
            if config:
                connection = get_connection(
                    host=config.smtp_host,
                    port=config.smtp_port,
                    username=config.username,
                    password=config.password,
                    use_tls=config.smtp_use_tls,
                    use_ssl=config.smtp_use_ssl,
                    fail_silently=False
                )
                from_email = f'"{config.from_name}" <{config.email_address}>' if config.from_name else config.email_address
                reply_to = [config.reply_to] if config.reply_to else None
            else:
                # Fallback aux paramètres Django
                connection = get_connection(fail_silently=False)
                from_email = settings.DEFAULT_FROM_EMAIL
                reply_to = None

            # Créer le message
            msg = EmailMultiAlternatives(
                subject=email_envoye.sujet,
                body=email_envoye.corps_texte or email_envoye.corps_html,
                from_email=from_email,
                to=[email_envoye.destinataire],
                cc=email_envoye.destinataires_cc,
                bcc=email_envoye.destinataires_bcc,
                reply_to=reply_to,
                connection=connection
            )

            # Ajouter la version HTML
            if email_envoye.corps_html:
                msg.attach_alternative(email_envoye.corps_html, "text/html")

            # Ajouter les pièces jointes
            for pj in email_envoye.pieces_jointes:
                if 'path' in pj and 'nom' in pj:
                    try:
                        with open(pj['path'], 'rb') as f:
                            msg.attach(pj['nom'], f.read())
                    except Exception as e:
                        logger.warning(f"Impossible d'attacher {pj['nom']}: {e}")

            # Envoyer
            msg.send()

            # Marquer comme envoyé
            email_envoye.statut = EmailEnvoye.Statut.ENVOYE
            email_envoye.date_envoi = timezone.now()
            email_envoye.erreur = ''
            email_envoye.save(update_fields=['statut', 'date_envoi', 'erreur', 'updated_at'])

            logger.info(f"Email envoyé à {email_envoye.destinataire}: {email_envoye.sujet}")
            return True

        except Exception as e:
            email_envoye.statut = EmailEnvoye.Statut.ECHEC
            email_envoye.erreur = str(e)
            email_envoye.save(update_fields=['statut', 'erreur', 'updated_at'])

            logger.error(f"Échec envoi email {email_envoye.id}: {e}")
            return False

    def test_configuration(self, configuration: ConfigurationEmail) -> Tuple[bool, str]:
        """
        Teste une configuration email.

        Args:
            configuration: Configuration à tester

        Returns:
            Tuple (succès, message)
        """
        try:
            if configuration.type_config == ConfigurationEmail.TypeConfig.SMTP:
                return self._test_smtp(configuration)
            elif configuration.type_config in [ConfigurationEmail.TypeConfig.IMAP, ConfigurationEmail.TypeConfig.POP3]:
                return self._test_imap(configuration)
            else:
                return False, f"Type de configuration non supporté: {configuration.type_config}"
        except Exception as e:
            return False, str(e)

    def _test_smtp(self, config: ConfigurationEmail) -> Tuple[bool, str]:
        """Teste une configuration SMTP."""
        try:
            if config.smtp_use_ssl:
                server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10)
                if config.smtp_use_tls:
                    server.starttls()

            server.login(config.username, config.password)
            server.quit()

            return True, "Connexion SMTP réussie"
        except smtplib.SMTPAuthenticationError:
            return False, "Erreur d'authentification SMTP"
        except smtplib.SMTPConnectError as e:
            return False, f"Impossible de se connecter au serveur SMTP: {e}"
        except Exception as e:
            return False, f"Erreur SMTP: {e}"

    def _test_imap(self, config: ConfigurationEmail) -> Tuple[bool, str]:
        """Teste une configuration IMAP."""
        try:
            if config.imap_use_ssl:
                server = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
            else:
                server = imaplib.IMAP4(config.imap_host, config.imap_port)

            server.login(config.username, config.password)
            server.select(config.imap_dossier or 'INBOX')
            server.logout()

            return True, "Connexion IMAP réussie"
        except imaplib.IMAP4.error as e:
            return False, f"Erreur IMAP: {e}"
        except Exception as e:
            return False, f"Erreur: {e}"

    def fetch_emails(
        self,
        configuration: ConfigurationEmail = None,
        limit: int = 50,
        unseen_only: bool = True
    ) -> List[EmailRecu]:
        """
        Récupère les emails depuis le serveur IMAP.

        Args:
            configuration: Configuration IMAP à utiliser
            limit: Nombre maximum d'emails à récupérer
            unseen_only: Si True, ne récupère que les emails non lus

        Returns:
            Liste des EmailRecu créés
        """
        config = configuration or self.configuration
        if not config:
            config = ConfigurationEmail.objects.filter(
                type_config__in=[
                    ConfigurationEmail.TypeConfig.IMAP,
                    ConfigurationEmail.TypeConfig.POP3
                ],
                actif=True
            ).first()

        if not config:
            logger.warning("Aucune configuration IMAP/POP3 trouvée")
            return []

        try:
            if config.imap_use_ssl:
                server = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
            else:
                server = imaplib.IMAP4(config.imap_host, config.imap_port)

            server.login(config.username, config.password)
            server.select(config.imap_dossier or 'INBOX')

            # Rechercher les emails
            search_criteria = 'UNSEEN' if unseen_only else 'ALL'
            _, message_numbers = server.search(None, search_criteria)

            emails_crees = []
            message_ids = message_numbers[0].split()[-limit:] if message_numbers[0] else []

            for num in message_ids:
                try:
                    email_recu = self._parse_email(server, num, config)
                    if email_recu:
                        emails_crees.append(email_recu)
                except Exception as e:
                    logger.error(f"Erreur parsing email {num}: {e}")

            server.logout()
            return emails_crees

        except Exception as e:
            logger.error(f"Erreur fetch emails: {e}")
            return []

    def _parse_email(
        self,
        server: imaplib.IMAP4,
        num: bytes,
        config: ConfigurationEmail
    ) -> Optional[EmailRecu]:
        """
        Parse un email depuis le serveur IMAP.

        Args:
            server: Connexion IMAP
            num: Numéro du message
            config: Configuration utilisée

        Returns:
            EmailRecu créé ou None
        """
        _, data = server.fetch(num, '(RFC822)')
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Message-ID unique
        message_id = msg.get('Message-ID', '')
        if not message_id:
            message_id = f"no-id-{timezone.now().timestamp()}-{num.decode()}"

        # Vérifier si déjà importé
        if EmailRecu.objects.filter(message_id=message_id).exists():
            return None

        # Parser l'expéditeur
        from_header = msg.get('From', '')
        expediteur_nom = ''
        expediteur_email = from_header
        if '<' in from_header:
            parts = from_header.split('<')
            expediteur_nom = parts[0].strip().strip('"')
            expediteur_email = parts[1].strip('>')

        # Parser le sujet
        sujet = ''
        if msg.get('Subject'):
            decoded = decode_header(msg.get('Subject'))
            sujet = ''.join(
                part.decode(charset or 'utf-8') if isinstance(part, bytes) else part
                for part, charset in decoded
            )

        # Parser les destinataires
        destinataires = [addr.strip() for addr in msg.get('To', '').split(',') if addr.strip()]
        destinataires_cc = [addr.strip() for addr in msg.get('Cc', '').split(',') if addr.strip()]

        # Parser la date
        date_str = msg.get('Date', '')
        try:
            date_reception = email.utils.parsedate_to_datetime(date_str)
        except Exception:
            date_reception = timezone.now()

        # Parser le corps
        corps_html = ''
        corps_texte = ''
        pieces_jointes = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                if 'attachment' in content_disposition:
                    # Pièce jointe
                    filename = part.get_filename()
                    if filename:
                        pieces_jointes.append({
                            'nom': filename,
                            'type': content_type,
                            'taille': len(part.get_payload(decode=True) or b'')
                        })
                elif content_type == 'text/plain':
                    corps_texte = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == 'text/html':
                    corps_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode('utf-8', errors='ignore')
                if content_type == 'text/html':
                    corps_html = text
                else:
                    corps_texte = text

        # Créer l'enregistrement
        email_recu = EmailRecu.objects.create(
            configuration=config,
            message_id=message_id,
            expediteur=expediteur_email,
            expediteur_nom=expediteur_nom,
            destinataires=destinataires,
            destinataires_cc=destinataires_cc,
            sujet=sujet[:500],
            corps_html=corps_html,
            corps_texte=corps_texte,
            pieces_jointes=pieces_jointes,
            date_reception=date_reception
        )

        # Lancer l'analyse IA si activée
        if config.analyse_ai_activee:
            from .tasks import analyser_email_task
            analyser_email_task.delay(str(email_recu.id))

        return email_recu

    def analyser_email(self, email_recu: EmailRecu) -> Dict:
        """
        Analyse un email avec l'IA.

        Args:
            email_recu: L'email à analyser

        Returns:
            Résultat de l'analyse
        """
        try:
            from documents.ai_service import AIService

            ai_service = AIService()

            # Préparer le contenu pour l'analyse
            contenu = f"""
            De: {email_recu.expediteur_nom} <{email_recu.expediteur}>
            Sujet: {email_recu.sujet}
            Date: {email_recu.date_reception}

            {email_recu.corps_texte or email_recu.corps_html}
            """

            # Appeler le service IA pour analyse
            prompt = """
            Analyse cet email et extrait les informations suivantes:
            1. Type d'email (demande_info, facturation, support, newsletter, spam, autre)
            2. Niveau d'urgence (haute, moyenne, basse)
            3. Résumé en une phrase
            4. Actions suggérées (liste)
            5. Si possible, identifie le client ou mandat concerné

            Réponds en JSON avec les clés: type, urgence, resume, actions, client_potentiel
            """

            # Note: L'implémentation dépend de votre service AI
            # Ceci est un exemple basique
            resultat = ai_service.analyze_text(contenu, prompt)

            # Mettre à jour l'email
            email_recu.analyse_effectuee = True
            email_recu.analyse_resultat = resultat
            email_recu.save(update_fields=['analyse_effectuee', 'analyse_resultat', 'updated_at'])

            # Marquer comme important si urgence haute
            if resultat.get('urgence') == 'haute':
                email_recu.est_important = True
                email_recu.save(update_fields=['est_important'])

            return resultat

        except Exception as e:
            logger.error(f"Erreur analyse IA email {email_recu.id}: {e}")
            email_recu.analyse_effectuee = True
            email_recu.analyse_resultat = {'erreur': str(e)}
            email_recu.save(update_fields=['analyse_effectuee', 'analyse_resultat', 'updated_at'])
            return {'erreur': str(e)}


# Instance singleton pour usage simple
email_service = EmailService()
