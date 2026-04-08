# core/views/two_factor_views.py
"""
Vues pour l'authentification à deux facteurs (TOTP).
- TwoFactorVerifyView: API endpoint pour valider le code OTP après login (mobile/API)
- TwoFactorSetupView / TwoFactorDisableView: pages web pour le template settings.html
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class TwoFactorVerifyView(APIView):
    """
    POST /api/v1/auth/2fa/verify/
    Vérifie le code TOTP (ou code de secours) et retourne les JWT tokens.

    Body: { "temp_token": "...", "code": "123456" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from ..services.two_factor_service import verify_temp_2fa_token
        from ..jwt_serializers import CustomTokenObtainPairSerializer

        temp_token = request.data.get('temp_token', '')
        code = request.data.get('code', '').strip()

        if not temp_token or not code:
            return Response(
                {'error': 'temp_token et code sont requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier le token temporaire
        user_id = verify_temp_2fa_token(temp_token)
        if not user_id:
            return Response(
                {'error': 'Token expiré ou invalide. Veuillez vous reconnecter.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Utilisateur introuvable'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Essayer d'abord le code TOTP, puis un code de secours
        if user.verify_totp(code):
            pass  # OK
        elif user.verify_backup_code(code):
            pass  # OK, code de secours consommé
        else:
            return Response(
                {'error': 'Code invalide'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Générer les vrais JWT tokens
        refresh = RefreshToken.for_user(user)

        # Ajouter les custom claims
        refresh['email'] = user.email
        refresh['name'] = user.get_full_name() or user.username

        data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': CustomTokenObtainPairSerializer._build_user_data(user),
        }

        # Mettre à jour last_login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response(data)


class TwoFactorSetupWebView(LoginRequiredMixin, View):
    """
    POST /settings/2fa/setup/
    Génère le secret TOTP et redirige vers settings avec le QR code en session.
    """

    def post(self, request):
        user = request.user
        if user.two_factor_enabled:
            messages.warning(request, _("L'authentification 2FA est déjà activée."))
            return redirect('core:settings')

        raw_secret = user.generate_totp_secret()
        user.save(update_fields=['totp_secret'])

        uri = user.get_totp_uri()
        from ..services.two_factor_service import generate_qr_code_base64
        qr_base64 = generate_qr_code_base64(uri)

        # Stocker en session pour afficher dans le template
        request.session['2fa_setup'] = {
            'secret': raw_secret,
            'qr_code': f"data:image/png;base64,{qr_base64}",
        }

        return redirect('core:settings')


class TwoFactorEnableWebView(LoginRequiredMixin, View):
    """
    POST /settings/2fa/enable/
    Vérifie le code TOTP soumis depuis le formulaire web et active la 2FA.
    """

    def post(self, request):
        user = request.user
        code = request.POST.get('code', '').strip()

        if user.two_factor_enabled:
            messages.warning(request, _("L'authentification 2FA est déjà activée."))
            return redirect('core:settings')

        if not user.totp_secret:
            messages.error(request, _("Veuillez d'abord configurer la 2FA."))
            return redirect('core:settings')

        if not code or not user.verify_totp(code):
            messages.error(request, _("Code invalide. Veuillez réessayer."))
            return redirect('core:settings')

        backup_codes = user.generate_backup_codes()
        user.enable_2fa()
        user.save(update_fields=['backup_codes'])

        # Nettoyer la session de setup
        request.session.pop('2fa_setup', None)

        # Stocker les codes de secours en session pour affichage unique
        request.session['2fa_backup_codes'] = backup_codes

        messages.success(request, _("Authentification à deux facteurs activée avec succès !"))
        return redirect('core:settings')


class TwoFactorDisableWebView(LoginRequiredMixin, View):
    """
    POST /settings/2fa/disable/
    Désactive la 2FA après vérification du mot de passe.
    """

    def post(self, request):
        user = request.user
        password = request.POST.get('password', '')

        if not user.two_factor_enabled:
            messages.warning(request, _("L'authentification 2FA n'est pas activée."))
            return redirect('core:settings')

        if not user.check_password(password):
            messages.error(request, _("Mot de passe incorrect."))
            return redirect('core:settings')

        user.disable_2fa()
        messages.success(request, _("Authentification à deux facteurs désactivée."))
        return redirect('core:settings')
