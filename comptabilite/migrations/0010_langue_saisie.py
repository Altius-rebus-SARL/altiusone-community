# Safe idempotent migration — adds langue_saisie only if not present.

from django.db import migrations, models


def add_langue_saisie_if_missing(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    tables = [
        'classes_comptables', 'comptes', 'ecritures_comptables', 'journaux',
        'lettrages', 'pieces_comptables', 'plans_comptables',
        'types_pieces_comptables', 'types_plans_comptables',
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
        ('comptabilite', '0009_typepiececomptable_dossier_classement'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(model_name='classecomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='compte', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='ecriturecomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='journal', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='lettrage', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='piececomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='plancomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='typepiececomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='typeplancomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
            ],
            database_operations=[
                migrations.RunPython(add_langue_saisie_if_missing, migrations.RunPython.noop),
            ],
        ),
    ]
