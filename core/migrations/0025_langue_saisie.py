# Safe idempotent migration — adds langue_saisie only if not present.

from django.db import migrations


def add_langue_saisie_if_missing(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    tables = [
        'acces_mandats', 'clients', 'collaborateurs_fiduciaire', 'contacts',
        'exercices_comptables', 'fichiers_joints', 'invitations', 'mandats',
        'modeles_document_pdf', 'notifications', 'parametres_metier',
        'taches', 'tiers',
    ]
    for table in tables:
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'langue_saisie'",
            [table]
        )
        if not cursor.fetchone():
            cursor.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "langue_saisie" '
                f"varchar(5) NOT NULL DEFAULT ''"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_mandat_plan_comptable_actif'),
    ]

    operations = [
        migrations.RunPython(add_langue_saisie_if_missing, migrations.RunPython.noop),
    ]
