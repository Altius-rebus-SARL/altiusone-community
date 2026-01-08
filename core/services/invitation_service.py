"""
Service de gestion des invitations.
"""
import logging
from typing import Optional, Dict, List
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from core.models import Invitation, Role, Mandat, AccesMandat

User = get_user_model()
logger = logging.getLogger(__name__)


class InvitationService:
    """
    Service pour gérer le cycle de vie des invitations.

    Fonctionnalités:
    - Création d'invitations (staff ou client)
    - Validation de tokens
    - Acceptation d'invitations
    - Renvoi d'invitations
    - Annulation d'invitations
    """

    @staticmethod
    def creer_invitation_staff(
        email: str,
        invite_par: User,
        role: Role = None,
        message: str = '',
        forcer_changement_mdp: bool = True
    ) -> Invitation:
        """
        Crée une invitation pour un collaborateur staff.

        Args:
            email: Email de l'invité
            invite_par: Utilisateur qui invite
            role: Rôle à attribuer (optionnel)
            message: Message personnalisé
            forcer_changement_mdp: Forcer le changement de mot de passe

        Returns:
            Invitation créée
        """
        # Vérifier que l'invitant peut inviter des staff
        if not invite_par.is_superuser and not invite_par.is_manager():
            raise PermissionError("Seuls les managers peuvent inviter des collaborateurs")

        # Vérifier si l'email existe déjà
        if User.objects.filter(email=email).exists():
            raise ValueError(f"Un utilisateur avec l'email {email} existe déjà")

        # Vérifier si une invitation en attente existe
        existing = Invitation.objects.filter(
            email=email,
            statut=Invitation.Statut.EN_ATTENTE
        ).first()
        if existing:
            raise ValueError(f"Une invitation en attente existe déjà pour {email}")

        # Calculer la date d'expiration
        expiry_days = getattr(settings, 'INVITATION_EXPIRY_DAYS', 7)
        date_expiration = timezone.now() + timedelta(days=expiry_days)

        invitation = Invitation.objects.create(
            email=email,
            type_invitation=Invitation.TypeInvitation.STAFF,
            date_expiration=date_expiration,
            invite_par=invite_par,
            role_preassigne=role,
            forcer_changement_mdp=forcer_changement_mdp,
            message_personnalise=message,
            created_by=invite_par
        )

        # Envoyer l'email d'invitation
        InvitationService._envoyer_email_invitation(invitation)

        logger.info(f"Invitation staff créée pour {email} par {invite_par.username}")
        return invitation

    @staticmethod
    def creer_invitation_client(
        email: str,
        invite_par: User,
        mandat: Mandat,
        permissions: List[Permission] = None,
        est_responsable: bool = False,
        limite_invitations: int = 5,
        message: str = '',
        forcer_changement_mdp: bool = True
    ) -> Invitation:
        """
        Crée une invitation pour un client externe.

        Args:
            email: Email de l'invité
            invite_par: Utilisateur qui invite
            mandat: Mandat concerné
            permissions: Permissions à accorder sur le mandat
            est_responsable: Si True, l'invité sera responsable du mandat côté client
            limite_invitations: Nombre d'invitations que le responsable pourra envoyer
            message: Message personnalisé
            forcer_changement_mdp: Forcer le changement de mot de passe

        Returns:
            Invitation créée
        """
        # Vérifier les permissions de l'invitant
        if invite_par.is_client_user():
            # Un client peut inviter uniquement s'il est responsable du mandat
            if not invite_par.peut_inviter_pour_mandat(mandat):
                raise PermissionError(
                    "Vous n'avez pas le droit d'inviter pour ce mandat ou "
                    "vous avez atteint votre limite d'invitations"
                )
        elif not (invite_par.is_superuser or invite_par.is_manager()):
            raise PermissionError("Vous n'avez pas le droit d'inviter des clients")

        # Vérifier si l'email existe déjà
        if User.objects.filter(email=email).exists():
            raise ValueError(f"Un utilisateur avec l'email {email} existe déjà")

        # Vérifier si une invitation en attente existe pour ce mandat
        existing = Invitation.objects.filter(
            email=email,
            mandat=mandat,
            statut=Invitation.Statut.EN_ATTENTE
        ).first()
        if existing:
            raise ValueError(f"Une invitation en attente existe déjà pour {email} sur ce mandat")

        # Calculer la date d'expiration
        expiry_days = getattr(settings, 'INVITATION_EXPIRY_DAYS', 7)
        date_expiration = timezone.now() + timedelta(days=expiry_days)

        # Trouver le rôle CLIENT par défaut
        role_client = Role.objects.filter(code=Role.CLIENT, actif=True).first()

        invitation = Invitation.objects.create(
            email=email,
            type_invitation=Invitation.TypeInvitation.CLIENT,
            date_expiration=date_expiration,
            invite_par=invite_par,
            mandat=mandat,
            role_preassigne=role_client,
            est_responsable_prevu=est_responsable,
            limite_invitations_prevue=limite_invitations,
            forcer_changement_mdp=forcer_changement_mdp,
            message_personnalise=message,
            created_by=invite_par
        )

        # Ajouter les permissions
        if permissions:
            invitation.permissions_acces.set(permissions)

        # Si l'invitant est un client, décrémenter son compteur d'invitations
        if invite_par.is_client_user():
            acces = invite_par.acces_mandats.filter(
                mandat=mandat,
                est_responsable=True,
                is_active=True
            ).first()
            if acces:
                acces.utiliser_invitation()

        # Envoyer l'email d'invitation
        InvitationService._envoyer_email_invitation(invitation)

        logger.info(f"Invitation client créée pour {email} sur mandat {mandat.numero}")
        return invitation

    @staticmethod
    def valider_token(token: str) -> Optional[Invitation]:
        """
        Valide un token d'invitation.

        Args:
            token: Token à valider

        Returns:
            Invitation si valide, None sinon
        """
        try:
            invitation = Invitation.objects.get(token=token)

            if not invitation.est_valide():
                # Marquer comme expirée si nécessaire
                if invitation.statut == Invitation.Statut.EN_ATTENTE:
                    invitation.marquer_expiree()
                return None

            return invitation

        except Invitation.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def accepter_invitation(
        invitation: Invitation,
        password: str,
        first_name: str = '',
        last_name: str = '',
        phone: str = ''
    ) -> User:
        """
        Accepte une invitation et crée le compte utilisateur.

        Args:
            invitation: Invitation à accepter
            password: Mot de passe choisi
            first_name: Prénom
            last_name: Nom
            phone: Téléphone (optionnel)

        Returns:
            Utilisateur créé
        """
        if not invitation.est_valide():
            raise ValueError("Cette invitation n'est plus valide")

        # Vérifier à nouveau si l'email n'existe pas
        if User.objects.filter(email=invitation.email).exists():
            raise ValueError("Un compte existe déjà avec cet email")

        # Créer l'utilisateur
        user = User.objects.create_user(
            username=invitation.email,
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Configurer selon le type d'invitation
        if invitation.type_invitation == Invitation.TypeInvitation.STAFF:
            user.type_utilisateur = User.TypeUtilisateur.STAFF
            user.is_staff = True  # Accès admin Django si nécessaire
        else:
            user.type_utilisateur = User.TypeUtilisateur.CLIENT
            user.is_staff = False

        # Assigner le rôle
        if invitation.role_preassigne:
            user.role = invitation.role_preassigne

        # Autres champs
        user.phone = phone
        user.doit_changer_mot_de_passe = invitation.forcer_changement_mdp
        user.save()

        # Pour les invitations CLIENT, créer l'AccesMandat
        if invitation.type_invitation == Invitation.TypeInvitation.CLIENT and invitation.mandat:
            acces = AccesMandat.objects.create(
                utilisateur=user,
                mandat=invitation.mandat,
                est_responsable=invitation.est_responsable_prevu,
                limite_invitations=invitation.limite_invitations_prevue,
                invitations_restantes=invitation.limite_invitations_prevue,
                accorde_par=invitation.invite_par,
                created_by=invitation.invite_par
            )

            # Ajouter les permissions
            if invitation.permissions_acces.exists():
                acces.permissions.set(invitation.permissions_acces.all())

        # Marquer l'invitation comme acceptée
        invitation.accepter(user)

        # Envoyer un email de bienvenue
        InvitationService._envoyer_email_bienvenue(user, invitation)

        logger.info(f"Invitation acceptée: {user.email} (type: {invitation.type_invitation})")
        return user

    @staticmethod
    def renvoyer_invitation(invitation: Invitation, renvoye_par: User) -> Invitation:
        """
        Renvoie une invitation (crée un nouveau token et prolonge l'expiration).

        Args:
            invitation: Invitation à renvoyer
            renvoye_par: Utilisateur qui renvoie

        Returns:
            Invitation mise à jour
        """
        if invitation.statut != Invitation.Statut.EN_ATTENTE:
            # Créer une nouvelle invitation si l'ancienne n'est plus en attente
            if invitation.type_invitation == Invitation.TypeInvitation.STAFF:
                return InvitationService.creer_invitation_staff(
                    email=invitation.email,
                    invite_par=renvoye_par,
                    role=invitation.role_preassigne,
                    message=invitation.message_personnalise,
                    forcer_changement_mdp=invitation.forcer_changement_mdp
                )
            else:
                return InvitationService.creer_invitation_client(
                    email=invitation.email,
                    invite_par=renvoye_par,
                    mandat=invitation.mandat,
                    permissions=list(invitation.permissions_acces.all()),
                    est_responsable=invitation.est_responsable_prevu,
                    limite_invitations=invitation.limite_invitations_prevue,
                    message=invitation.message_personnalise,
                    forcer_changement_mdp=invitation.forcer_changement_mdp
                )

        # Générer un nouveau token et prolonger l'expiration
        expiry_days = getattr(settings, 'INVITATION_EXPIRY_DAYS', 7)
        invitation.token = Invitation.generer_token()
        invitation.date_expiration = timezone.now() + timedelta(days=expiry_days)
        invitation.save(update_fields=['token', 'date_expiration', 'updated_at'])

        # Renvoyer l'email
        InvitationService._envoyer_email_invitation(invitation)

        logger.info(f"Invitation renvoyée pour {invitation.email}")
        return invitation

    @staticmethod
    def annuler_invitation(invitation: Invitation, annule_par: User) -> None:
        """
        Annule une invitation.

        Args:
            invitation: Invitation à annuler
            annule_par: Utilisateur qui annule
        """
        if invitation.statut != Invitation.Statut.EN_ATTENTE:
            raise ValueError("Seules les invitations en attente peuvent être annulées")

        # Vérifier les permissions
        if not annule_par.is_superuser:
            if invitation.invite_par != annule_par and not annule_par.is_manager():
                raise PermissionError("Vous ne pouvez pas annuler cette invitation")

        invitation.annuler()
        logger.info(f"Invitation annulée pour {invitation.email} par {annule_par.username}")

    @staticmethod
    def nettoyer_invitations_expirees() -> int:
        """
        Marque toutes les invitations expirées.

        Returns:
            Nombre d'invitations marquées comme expirées
        """
        now = timezone.now()
        expired = Invitation.objects.filter(
            statut=Invitation.Statut.EN_ATTENTE,
            date_expiration__lt=now
        )
        count = expired.count()
        expired.update(statut=Invitation.Statut.EXPIREE)

        if count > 0:
            logger.info(f"{count} invitations marquées comme expirées")

        return count

    @staticmethod
    def _envoyer_email_invitation(invitation: Invitation) -> None:
        """
        Envoie l'email d'invitation.
        """
        from mailing.services import email_service

        template_code = (
            'INVITATION_STAFF'
            if invitation.type_invitation == Invitation.TypeInvitation.STAFF
            else 'INVITATION_CLIENT'
        )

        context = {
            'invitation': invitation,
            'invite_par': invitation.invite_par,
            'lien_acceptation': invitation.get_absolute_url(),
            'date_expiration': invitation.date_expiration,
            'message_personnalise': invitation.message_personnalise,
            'mandat': invitation.mandat,
        }

        email_service.send_template_email(
            destinataire=invitation.email,
            template_code=template_code,
            context=context,
            content_type='invitation',
            object_id=str(invitation.id)
        )

    @staticmethod
    def _envoyer_email_bienvenue(user: User, invitation: Invitation) -> None:
        """
        Envoie un email de bienvenue après acceptation.
        """
        from mailing.services import email_service

        template_code = 'WELCOME'

        context = {
            'user': user,
            'prenom': user.first_name,
            'nom': user.last_name,
            'type_utilisateur': user.get_type_utilisateur_display(),
            'mandat': invitation.mandat,
            'doit_changer_mdp': user.doit_changer_mot_de_passe,
        }

        email_service.send_template_email(
            destinataire=user.email,
            template_code=template_code,
            context=context,
            content_type='welcome',
            object_id=str(user.id)
        )


# Tâches Celery
from celery import shared_task


@shared_task
def nettoyer_invitations_expirees_task():
    """Tâche Celery pour nettoyer les invitations expirées."""
    return InvitationService.nettoyer_invitations_expirees()
