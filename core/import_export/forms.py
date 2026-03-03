# core/import_export/forms.py
"""
Formulaires pour l'import/export de données.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ImportForm(forms.Form):
    """
    Formulaire d'import de fichier.

    Champs:
    - import_file: Le fichier à importer (CSV ou Excel)
    - dry_run: Option pour simuler l'import sans modifier la DB
    """

    import_file = forms.FileField(
        label=_("Fichier à importer"),
        help_text=_("Formats acceptés: CSV (.csv) ou Excel (.xlsx)"),
        widget=forms.FileInput(attrs={
            'accept': '.csv,.xlsx,.xls',
            'class': 'form-control',
        })
    )

    dry_run = forms.BooleanField(
        label=_("Simulation uniquement"),
        help_text=_("Cochez pour voir ce qui serait importé sans modifier les données"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def clean_import_file(self):
        """Valide le fichier importé."""
        file = self.cleaned_data.get('import_file')

        if not file:
            raise forms.ValidationError(_("Veuillez sélectionner un fichier."))

        # Vérifier l'extension
        filename = file.name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            raise forms.ValidationError(
                _("Format de fichier non supporté. Utilisez CSV ou Excel (.xlsx)")
            )

        # Vérifier la taille
        max_size = getattr(settings, 'IMPORT_EXPORT_MAX_FILE_SIZE', 10 * 1024 * 1024)
        if file.size > max_size:
            raise forms.ValidationError(
                _("Le fichier est trop volumineux. Taille maximale: {size}MB").format(
                    size=max_size // (1024 * 1024)
                )
            )

        return file


class ExportForm(forms.Form):
    """
    Formulaire de choix du format d'export.
    """

    FORMAT_CHOICES = [
        ('xlsx', _('Excel (.xlsx)')),
        ('csv', _('CSV')),
    ]

    format = forms.ChoiceField(
        label=_("Format d'export"),
        choices=FORMAT_CHOICES,
        initial='xlsx',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        })
    )
