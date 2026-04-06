# core/templatetags/translation_tags.py
"""
Template tags pour le rendu de champs traduits avec onglets et drapeaux.

Usage dans les templates:
    {% load translation_tags %}

    {# Rendu d'un champ traduit avec onglets FR/DE/IT/EN #}
    {% translated_field form "titre" %}

    {# Avec label personnalise #}
    {% translated_field form "description" label="Description du mandat" %}

    {# Champ obligatoire #}
    {% translated_field form "titre" required=True %}
"""

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

register = template.Library()

LANGUAGE_FLAGS = {
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "en": "🇬🇧",
}

LANGUAGE_LABELS = {
    "fr": "FR",
    "de": "DE",
    "it": "IT",
    "en": "EN",
}


def _get_languages():
    return getattr(settings, "MODELTRANSLATION_LANGUAGES", ("fr", "de", "it", "en"))


def _get_default_language():
    return getattr(settings, "MODELTRANSLATION_DEFAULT_LANGUAGE", "fr")


@register.inclusion_tag(
    "components/forms/translated_field.html", takes_context=True
)
def translated_field(context, form, field_name, **kwargs):
    """
    Regroupe les champs traduits (field_fr, field_de, ...) en onglets avec drapeaux.

    Utilisation:
        {% translated_field form "titre" %}
        {% translated_field form "description" required=True label="Mon label" %}
    """
    languages = _get_languages()
    default_lang = _get_default_language()

    label = kwargs.get("label", "")
    required = kwargs.get("required", False)
    help_text_override = kwargs.get("help_text", "")

    tabs = []
    for lang in languages:
        lang_field_name = f"{field_name}_{lang}"
        bound_field = form[lang_field_name] if lang_field_name in form.fields else None
        if bound_field is None:
            continue

        if not label and bound_field:
            # Utiliser le label du champ par defaut (sans le suffixe de langue)
            raw_label = str(bound_field.label)
            # Nettoyer les suffixes de langue ajoutes par modeltranslation
            for suffix in (" [fr]", " [de]", " [it]", " [en]",
                           " (fr)", " (de)", " (it)", " (en)"):
                raw_label = raw_label.replace(suffix, "")
            label = raw_label

        # Detecter si le champ a des erreurs
        has_errors = bool(bound_field.errors) if bound_field else False

        tabs.append({
            "lang": lang,
            "flag": LANGUAGE_FLAGS.get(lang, ""),
            "label": LANGUAGE_LABELS.get(lang, lang.upper()),
            "field": bound_field,
            "is_default": lang == default_lang,
            "has_errors": has_errors,
        })

    # Si aucun champ traduit trouve, essayer le champ de base
    if not tabs:
        bound_field = form[field_name] if field_name in form.fields else None
        if bound_field:
            return {
                "tabs": [],
                "single_field": bound_field,
                "label": label or str(bound_field.label),
                "required": required,
                "field_name": field_name,
                "help_text": help_text_override,
                "has_any_errors": bool(bound_field.errors),
            }

    has_any_errors = any(t["has_errors"] for t in tabs)

    return {
        "tabs": tabs,
        "single_field": None,
        "label": label,
        "required": required,
        "field_name": field_name,
        "help_text": help_text_override,
        "has_any_errors": has_any_errors,
        "default_lang": default_lang,
    }
