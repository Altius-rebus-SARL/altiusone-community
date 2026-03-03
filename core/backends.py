from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """
    Authentification par email ou nom d'utilisateur.
    Permet aux utilisateurs de se connecter avec leur email
    en plus de leur nom d'utilisateur standard.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None or password is None:
            return None

        # Essayer d'abord par username (comportement par défaut)
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Si pas trouvé par username, essayer par email
            try:
                user = UserModel.objects.get(email__iexact=username)
            except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
