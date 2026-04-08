# Safe idempotent migration — adds langue_saisie only if not present.

from django.db import migrations, models


def add_langue_saisie_if_missing(apps, schema_editor):
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
        ('documents', '0006_document_fichier_max_length_500'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(model_name='categoriedocument', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='conversation', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='document', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='documentrelation', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='dossier', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='mandatdigest', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='mandatinsight', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='message', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='sourcedocument', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='traitementdocument', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='typedocument', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='versiondocument', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
            ],
            database_operations=[
                migrations.RunPython(add_langue_saisie_if_missing, migrations.RunPython.noop),
            ],
        ),
    ]
