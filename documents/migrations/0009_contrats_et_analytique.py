# Safe migration — adds langue_saisie only if column doesn't exist yet.
# Required because some instances already have the column (added manually).

from django.db import migrations, models


def add_column_if_not_exists(apps, schema_editor):
    """Add langue_saisie to all documents tables, skipping if already present."""
    connection = schema_editor.connection
    tables = [
        'categories_document', 'conversations', 'documents', 'documents_relations',
        'dossiers', 'mandat_digests', 'mandat_insights', 'messages_conversation',
        'sources_document', 'traitements_document', 'types_document', 'versions_document',
    ]
    for table in tables:
        cursor = connection.cursor()
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
            cursor.execute(
                f'CREATE INDEX IF NOT EXISTS "{table}_langue_saisie_idx" '
                f'ON "{table}" ("langue_saisie")'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_conversation_mandats_m2m'),
    ]

    operations = [
        migrations.RunPython(add_column_if_not_exists, migrations.RunPython.noop),
    ]
