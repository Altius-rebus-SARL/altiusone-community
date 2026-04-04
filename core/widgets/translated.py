# core/widgets/translated.py
"""
Widgets multilingues avec onglets et drapeaux pour django-modeltranslation.

Usage dans un formulaire:
    from core.widgets import TranslatedCharWidget, TranslatedTextareaWidget

    class MyForm(forms.ModelForm):
        class Meta:
            model = MyModel
            fields = [...]
            widgets = {
                "titre_fr": TranslatedCharWidget(lang="fr"),
                "titre_de": TranslatedCharWidget(lang="de"),
                ...
            }

Ou plus simplement, utiliser le template tag {% translated_field %} dans les templates
qui regroupe automatiquement les champs _fr, _de, _it, _en en onglets.
"""

from django import forms
from django.conf import settings


LANGUAGE_FLAGS = {
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "en": "🇬🇧",
}

LANGUAGE_LABELS = {
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "en": "English",
}


def get_languages():
    """Retourne les langues configurées dans MODELTRANSLATION_LANGUAGES."""
    return getattr(settings, "MODELTRANSLATION_LANGUAGES", ("fr", "de", "it", "en"))


class TranslatedCharWidget(forms.TextInput):
    """TextInput marqué avec un indicateur de langue."""

    def __init__(self, lang=None, *args, **kwargs):
        self.lang = lang
        super().__init__(*args, **kwargs)
        if lang:
            flag = LANGUAGE_FLAGS.get(lang, "")
            self.attrs.setdefault("class", "form-control translated-input")
            self.attrs["data-lang"] = lang
            self.attrs["placeholder"] = f"{flag} {LANGUAGE_LABELS.get(lang, lang)}"


class TranslatedTextareaWidget(forms.Textarea):
    """Textarea marqué avec un indicateur de langue."""

    def __init__(self, lang=None, rows=3, *args, **kwargs):
        self.lang = lang
        super().__init__(*args, **kwargs)
        if lang:
            flag = LANGUAGE_FLAGS.get(lang, "")
            self.attrs.setdefault("class", "form-control translated-input")
            self.attrs["data-lang"] = lang
            self.attrs["rows"] = rows
            self.attrs["placeholder"] = f"{flag} {LANGUAGE_LABELS.get(lang, lang)}"


class TranslatedRichTextareaWidget(forms.Textarea):
    """Textarea riche (HTML) marqué avec un indicateur de langue."""

    def __init__(self, lang=None, rows=6, *args, **kwargs):
        self.lang = lang
        super().__init__(*args, **kwargs)
        if lang:
            flag = LANGUAGE_FLAGS.get(lang, "")
            self.attrs.setdefault("class", "form-control translated-input translated-rich")
            self.attrs["data-lang"] = lang
            self.attrs["rows"] = rows
            self.attrs["placeholder"] = f"{flag} {LANGUAGE_LABELS.get(lang, lang)}"
