# Safe idempotent migration — skips columns/tables that already exist.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def safe_add_columns(apps, schema_editor):
    """Add langue_saisie + dossier_classement only if not already present."""
    conn = schema_editor.connection
    cursor = conn.cursor()

    def col_exists(table, column):
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s", [table, column]
        )
        return cursor.fetchone() is not None

    # langue_saisie on all comptabilite tables
    for table in [
        'classes_comptables', 'comptes', 'ecritures_comptables', 'journaux',
        'lettrages', 'pieces_comptables', 'plans_comptables',
        'types_pieces_comptables', 'types_plans_comptables',
    ]:
        if not col_exists(table, 'langue_saisie'):
            cursor.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "langue_saisie" '
                f"varchar(5) NOT NULL DEFAULT ''"
            )

    # dossier_classement on types_piece_comptable
    if not col_exists('types_pieces_comptables', 'dossier_classement'):
        cursor.execute(
            'ALTER TABLE "types_pieces_comptables" ADD COLUMN "dossier_classement" '
            "varchar(100) NOT NULL DEFAULT ''"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0010_langue_saisie'),
        ('core', '0023_modelembedding'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                migrations.AddField(model_name='typepiececomptable', name='dossier_classement', field=models.CharField(blank=True, help_text='Nom du sous-dossier cible pour le classement automatique (ex: Comptabilité, Salaires)', max_length=100, verbose_name='Dossier de classement')),
            ],
            database_operations=[
                migrations.RunPython(safe_add_columns, migrations.RunPython.noop),
            ],
        ),
        migrations.CreateModel(
            name='AxeAnalytique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('langue_saisie', models.CharField(blank=True, db_index=True, default='', max_length=5, verbose_name='Langue de saisie')),
                ('code', models.CharField(max_length=50, verbose_name='Code')),
                ('libelle', models.CharField(max_length=200, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('obligatoire', models.BooleanField(default=False, verbose_name='Obligatoire')),
                ('ordre', models.IntegerField(default=0, verbose_name='Ordre')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('mandat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='axes_analytiques', to='core.mandat', verbose_name='Mandat')),
            ],
            options={
                'verbose_name': 'Axe analytique',
                'verbose_name_plural': 'Axes analytiques',
                'db_table': 'axes_analytiques',
                'ordering': ['ordre', 'code'],
                'unique_together': {('mandat', 'code')},
            },
        ),
        migrations.CreateModel(
            name='SectionAnalytique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('langue_saisie', models.CharField(blank=True, db_index=True, default='', max_length=5, verbose_name='Langue de saisie')),
                ('code', models.CharField(max_length=50, verbose_name='Code')),
                ('libelle', models.CharField(max_length=200, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('budget_annuel', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True, verbose_name='Budget annuel')),
                ('ordre', models.IntegerField(default=0, verbose_name='Ordre')),
                ('axe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='comptabilite.axeanalytique', verbose_name='Axe')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sous_sections', to='comptabilite.sectionanalytique', verbose_name='Section parente')),
                ('responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Responsable')),
            ],
            options={
                'verbose_name': 'Section analytique',
                'verbose_name_plural': 'Sections analytiques',
                'db_table': 'sections_analytiques',
                'ordering': ['axe', 'ordre', 'code'],
                'unique_together': {('axe', 'code')},
            },
        ),
        migrations.CreateModel(
            name='VentilationAnalytique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('langue_saisie', models.CharField(blank=True, db_index=True, default='', max_length=5, verbose_name='Langue de saisie')),
                ('pourcentage', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Pourcentage')),
                ('montant', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Montant')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('ecriture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ventilations_analytiques', to='comptabilite.ecriturecomptable', verbose_name='Écriture')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ventilations', to='comptabilite.sectionanalytique', verbose_name='Section')),
            ],
            options={
                'verbose_name': 'Ventilation analytique',
                'verbose_name_plural': 'Ventilations analytiques',
                'db_table': 'ventilations_analytiques',
                'indexes': [models.Index(fields=['ecriture', 'section'], name='ventilation_ecritur_4d0fe8_idx')],
            },
        ),
    ]
