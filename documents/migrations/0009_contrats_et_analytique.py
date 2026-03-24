# Safe idempotent migration — adds langue_saisie only if column doesn't exist.

from django.db import migrations


def add_column_if_not_exists(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    tables = [
        'categories_document', 'conversations', 'documents', 'document_relations',
        'dossiers', 'mandat_digests', 'mandat_insights', 'messages',
        'sources_document', 'traitements_document', 'types_document', 'versions_document',
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
        ('documents', '0008_conversation_mandats_m2m'),
    ]

    operations = [
        migrations.RunPython(add_column_if_not_exists, migrations.RunPython.noop),
    ]
