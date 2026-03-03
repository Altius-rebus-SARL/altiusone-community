"""
Crée les modèles PDF système par défaut pour chaque type de document.
Ignore les types déjà configurés.
"""
from django.core.management.base import BaseCommand

from core.models import ModeleDocumentPDF
from core.services.pdf_studio_styles import DEFAULTS


class Command(BaseCommand):
    help = "Initialise les modèles PDF système par défaut pour chaque type de document"

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for type_code, type_label in ModeleDocumentPDF.TypeDocument.choices:
            exists = ModeleDocumentPDF.objects.filter(
                type_document=type_code,
                mandat__isnull=True,
                est_defaut=True,
                is_active=True,
            ).exists()

            if exists:
                self.stdout.write(f"  Modèle système déjà existant pour {type_label}, ignoré.")
                skipped += 1
                continue

            defaults = DEFAULTS.get(type_code, {})

            ModeleDocumentPDF.objects.create(
                nom=f"{type_label} - Système",
                type_document=type_code,
                mandat=None,
                est_defaut=True,
                couleur_primaire=defaults.get('couleur_primaire', '#088178'),
                couleur_accent=defaults.get('couleur_accent', '#2c3e50'),
                couleur_texte=defaults.get('couleur_texte', '#333333'),
                police=defaults.get('police', 'Helvetica'),
                marge_haut=defaults.get('marge_haut', 20),
                marge_bas=defaults.get('marge_bas', 25),
                marge_gauche=defaults.get('marge_gauche', 20),
                marge_droite=defaults.get('marge_droite', 15),
                textes=defaults.get('textes', {}),
                blocs_visibles=defaults.get('blocs_visibles', {}),
                config=defaults.get('config', {}),
            )
            self.stdout.write(self.style.SUCCESS(f"  Créé: {type_label} - Système"))
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé: {created} modèle(s) créé(s), {skipped} ignoré(s)."
        ))
