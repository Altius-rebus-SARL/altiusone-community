from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def client_nom(client):
    """Retourne le nom du client de manière sécurisée"""
    if hasattr(client, "raison_sociale") and client.raison_sociale:
        return client.raison_sociale
    elif hasattr(client, "nom") and client.nom:
        return client.nom
    elif hasattr(client, "nom_complet"):
        return client.nom_complet()
    return str(client)


@register.filter
def client_adresse(client):
    """Retourne l'adresse du client formatée en HTML"""
    parts = []

    # Adresse principale
    if hasattr(client, "adresse") and client.adresse:
        parts.append(client.adresse)
    elif hasattr(client, "adresse_ligne1") and client.adresse_ligne1:
        parts.append(client.adresse_ligne1)

    # Complément d'adresse
    if hasattr(client, "complement_adresse") and client.complement_adresse:
        parts.append(client.complement_adresse)
    elif hasattr(client, "adresse_ligne2") and client.adresse_ligne2:
        parts.append(client.adresse_ligne2)

    # Ville
    ville_parts = []
    if hasattr(client, "code_postal") and client.code_postal:
        ville_parts.append(str(client.code_postal))
    if hasattr(client, "ville") and client.ville:
        ville_parts.append(client.ville)

    if ville_parts:
        parts.append(" ".join(ville_parts))

    # Email
    if hasattr(client, "email") and client.email:
        parts.append(client.email)

    return mark_safe("<br>".join(parts)) if parts else ""


@register.filter
def client_telephone(client):
    """Retourne le téléphone du client"""
    if hasattr(client, "telephone") and client.telephone:
        return client.telephone
    elif hasattr(client, "tel") and client.tel:
        return client.tel
    return ""


@register.simple_tag
def format_adresse_complete(client):
    """Formate une adresse complète avec tous les détails"""
    lines = []

    # Nom
    nom = client_nom(client)
    if nom:
        lines.append(f"<strong>{nom}</strong>")

    # Adresse
    adresse_html = client_adresse(client)
    if adresse_html:
        lines.append(adresse_html)

    # Téléphone
    tel = client_telephone(client)
    if tel:
        lines.append(tel)

    return mark_safe("<br>".join(lines))
