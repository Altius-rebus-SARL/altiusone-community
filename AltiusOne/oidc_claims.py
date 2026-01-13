"""
Validateur OIDC personnalisé pour AltiusOne.

Définit les informations utilisateur retournées via les endpoints OIDC
pour les applications clientes comme Docs (La Suite Numérique).

django-oauth-toolkit 3.x utilise un validateur personnalisé au lieu d'une
classe de claims séparée. Les claims additionnels sont retournés via
la méthode get_additional_claims() du validateur.
"""

from oauth2_provider.oauth2_validators import OAuth2Validator


class AltiusOneOAuth2Validator(OAuth2Validator):
    """
    Validateur OAuth2/OIDC personnalisé pour AltiusOne.

    Étend le validateur par défaut pour inclure les claims utilisateur
    standards OIDC (email, profile) dans les réponses userinfo et id_token.
    """

    # Mapping des claims vers leurs scopes requis
    # Les claims ne sont retournés que si le scope correspondant a été accordé
    oidc_claim_scope = {
        "sub": "openid",
        "email": "email",
        "email_verified": "email",
        "name": "profile",
        "given_name": "profile",
        "family_name": "profile",
        "preferred_username": "profile",
        "locale": "profile",
    }

    def get_additional_claims(self, request):
        """
        Retourne les claims additionnels basés sur les scopes accordés.

        Cette méthode est appelée par get_oidc_claims() pour construire
        la réponse userinfo et le contenu de l'id_token.

        Args:
            request: L'objet request OAuthLib contenant l'utilisateur et les scopes

        Returns:
            dict: Les claims additionnels (clé -> valeur ou callable)
        """
        user = request.user

        # Utiliser des lambdas pour retarder l'évaluation
        # (compatible avec le système de claims de django-oauth-toolkit)
        claims = {}

        # Claims email (scope: email)
        claims["email"] = lambda r: r.user.email
        claims["email_verified"] = lambda r: r.user.is_active

        # Claims profile (scope: profile)
        claims["name"] = lambda r: r.user.get_full_name() or r.user.username
        claims["given_name"] = lambda r: r.user.first_name or ""
        claims["family_name"] = lambda r: r.user.last_name or ""
        claims["preferred_username"] = lambda r: r.user.username
        claims["locale"] = lambda r: getattr(r.user, "langue", "fr") or "fr"

        return claims
