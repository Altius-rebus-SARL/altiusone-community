# core/mixins_forms.py
"""
Mixin pour les formulaires avec champs traduits via django-modeltranslation.

Usage:
    from core.mixins_forms import TranslationFormMixin

    class MonForm(TranslationFormMixin, forms.ModelForm):
        class Meta:
            model = MonModel
            fields = [...]

Le mixin detecte automatiquement les champs traduits (_fr, _de, _it, _en)
et leur applique la classe CSS 'form-control translated-input' + l'attribut data-lang.
"""

from django.conf import settings


class TranslationFormMixin:
    """
    Detecte les champs traduits et applique les attributs CSS/data-lang.
    Compatible avec le template tag {% translated_field %}.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        languages = getattr(
            settings, "MODELTRANSLATION_LANGUAGES", ("fr", "de", "it", "en")
        )
        suffixes = tuple(f"_{lang}" for lang in languages)

        for field_name, field in self.fields.items():
            for lang in languages:
                suffix = f"_{lang}"
                if field_name.endswith(suffix):
                    widget = field.widget
                    css = widget.attrs.get("class", "")
                    if "form-control" not in css:
                        css = f"form-control {css}".strip()
                    if "translated-input" not in css:
                        css = f"{css} translated-input"
                    widget.attrs["class"] = css
                    widget.attrs["data-lang"] = lang
                    break
