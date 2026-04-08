# Safe idempotent migration — adds langue_saisie only if not present.

from django.db import migrations, models


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
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(model_name='accesmandat', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='client', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='collaborateurfiduciaire', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='contact', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='exercicecomptable', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='fichierjoint', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='invitation', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='mandat', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='modeledocumentpdf', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='notification', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='parametremetier', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='tache', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
                migrations.AddField(model_name='tiers', name='langue_saisie', field=models.CharField(blank=True, db_index=True, default='', help_text='Langue de saisie', max_length=5, verbose_name='Langue de saisie')),
            ],
            database_operations=[
                migrations.RunPython(add_langue_saisie_if_missing, migrations.RunPython.noop),
            ],
        ),
    ]
