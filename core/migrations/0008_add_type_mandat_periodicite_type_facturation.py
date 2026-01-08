# Generated manually for TypeMandat, Periodicite, and TypeFacturation tables
# core/migrations/0008_add_type_mandat_periodicite_type_facturation.py

from django.db import migrations, models
import django.db.models.deletion
import uuid


def create_initial_periodicites(apps, schema_editor):
    """Créer les périodicités initiales basées sur les choices existants"""
    Periodicite = apps.get_model('core', 'Periodicite')

    periodicites = [
        {'code': 'MENSUEL', 'libelle': 'Mensuel', 'nombre_mois': 1, 'nombre_par_an': 12, 'ordre': 1},
        {'code': 'TRIMESTRIEL', 'libelle': 'Trimestriel', 'nombre_mois': 3, 'nombre_par_an': 4, 'ordre': 2},
        {'code': 'SEMESTRIEL', 'libelle': 'Semestriel', 'nombre_mois': 6, 'nombre_par_an': 2, 'ordre': 3},
        {'code': 'ANNUEL', 'libelle': 'Annuel', 'nombre_mois': 12, 'nombre_par_an': 1, 'ordre': 4},
        {'code': 'PONCTUEL', 'libelle': 'Ponctuel', 'nombre_mois': 0, 'nombre_par_an': 0, 'ordre': 5},
    ]

    for p in periodicites:
        Periodicite.objects.create(**p)


def create_initial_types_mandats(apps, schema_editor):
    """Créer les types de mandats initiaux basés sur les choices existants"""
    TypeMandat = apps.get_model('core', 'TypeMandat')

    types_mandats = [
        {'code': 'COMPTA', 'libelle': 'Comptabilité', 'icone': 'ph-calculator', 'couleur': 'primary', 'ordre': 1,
         'description': 'Tenue de la comptabilité générale et analytique', 'modules_actifs': ['compta']},
        {'code': 'TVA', 'libelle': 'TVA', 'icone': 'ph-percent', 'couleur': 'info', 'ordre': 2,
         'description': 'Déclarations et conseil TVA', 'modules_actifs': ['tva']},
        {'code': 'SALAIRES', 'libelle': 'Salaires', 'icone': 'ph-users', 'couleur': 'success', 'ordre': 3,
         'description': 'Gestion des salaires et charges sociales', 'modules_actifs': ['salaires']},
        {'code': 'FISCAL', 'libelle': 'Conseil fiscal', 'icone': 'ph-scales', 'couleur': 'warning', 'ordre': 4,
         'description': 'Conseil et optimisation fiscale', 'modules_actifs': ['fiscal']},
        {'code': 'REVISION', 'libelle': 'Révision', 'icone': 'ph-magnifying-glass', 'couleur': 'danger', 'ordre': 5,
         'description': 'Révision et audit des comptes', 'modules_actifs': ['revision']},
        {'code': 'CONSEIL', 'libelle': 'Conseil général', 'icone': 'ph-lightbulb', 'couleur': 'secondary', 'ordre': 6,
         'description': 'Conseil général en gestion d\'entreprise', 'modules_actifs': ['conseil']},
        {'code': 'CREATION', 'libelle': 'Création entreprise', 'icone': 'ph-rocket', 'couleur': 'primary', 'ordre': 7,
         'description': 'Accompagnement à la création d\'entreprise', 'modules_actifs': ['creation']},
        {'code': 'GLOBAL', 'libelle': 'Mandat global', 'icone': 'ph-globe', 'couleur': 'dark', 'ordre': 8,
         'description': 'Mandat complet incluant tous les services', 'modules_actifs': ['compta', 'tva', 'salaires', 'fiscal']},
    ]

    for t in types_mandats:
        TypeMandat.objects.create(**t)


def create_initial_types_facturation(apps, schema_editor):
    """Créer les types de facturation initiaux basés sur les choices existants"""
    TypeFacturation = apps.get_model('core', 'TypeFacturation')

    types_facturation = [
        {'code': 'FORFAIT', 'libelle': 'Forfait', 'ordre': 1,
         'description': 'Montant fixe pour la prestation',
         'necessite_forfait': True, 'necessite_taux_horaire': False},
        {'code': 'HORAIRE', 'libelle': 'Taux horaire', 'ordre': 2,
         'description': 'Facturation au temps passé',
         'necessite_forfait': False, 'necessite_taux_horaire': True},
        {'code': 'MIXTE', 'libelle': 'Mixte', 'ordre': 3,
         'description': 'Forfait de base + dépassement au taux horaire',
         'necessite_forfait': True, 'necessite_taux_horaire': True},
        {'code': 'ABONNEMENT', 'libelle': 'Abonnement', 'ordre': 4,
         'description': 'Forfait mensuel récurrent',
         'necessite_forfait': True, 'necessite_taux_horaire': False},
    ]

    for t in types_facturation:
        TypeFacturation.objects.create(**t)


def migrate_existing_mandats(apps, schema_editor):
    """Migrer les données existantes des mandats vers les nouvelles tables de référence"""
    Mandat = apps.get_model('core', 'Mandat')
    TypeMandat = apps.get_model('core', 'TypeMandat')
    Periodicite = apps.get_model('core', 'Periodicite')
    TypeFacturation = apps.get_model('core', 'TypeFacturation')

    # Cache pour éviter les requêtes répétées
    type_mandat_cache = {t.code: t for t in TypeMandat.objects.all()}
    periodicite_cache = {p.code: p for p in Periodicite.objects.all()}
    type_facturation_cache = {t.code: t for t in TypeFacturation.objects.all()}

    for mandat in Mandat.objects.all():
        updated = False

        # Migrer type_mandat
        if mandat.type_mandat and mandat.type_mandat in type_mandat_cache:
            mandat.type_mandat_ref = type_mandat_cache[mandat.type_mandat]
            updated = True

        # Migrer periodicite
        if mandat.periodicite and mandat.periodicite in periodicite_cache:
            mandat.periodicite_ref = periodicite_cache[mandat.periodicite]
            updated = True

        # Migrer type_facturation
        if mandat.type_facturation and mandat.type_facturation in type_facturation_cache:
            mandat.type_facturation_ref = type_facturation_cache[mandat.type_facturation]
            updated = True

        if updated:
            mandat.save()


def reverse_migrate_mandats(apps, schema_editor):
    """Reverse migration - copier les refs vers les champs texte"""
    Mandat = apps.get_model('core', 'Mandat')

    for mandat in Mandat.objects.select_related(
        'type_mandat_ref', 'periodicite_ref', 'type_facturation_ref'
    ).all():
        if mandat.type_mandat_ref:
            mandat.type_mandat = mandat.type_mandat_ref.code
        if mandat.periodicite_ref:
            mandat.periodicite = mandat.periodicite_ref.code
        if mandat.type_facturation_ref:
            mandat.type_facturation = mandat.type_facturation_ref.code
        mandat.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_auditlog_action'),
    ]

    operations = [
        # 1. Créer la table Periodicite
        migrations.CreateModel(
            name='Periodicite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='Code unique (ex: MENSUEL, TRIMESTRIEL)', max_length=30, unique=True, verbose_name='Code')),
                ('libelle', models.CharField(max_length=100, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('nombre_mois', models.PositiveSmallIntegerField(default=1, help_text="Nombre de mois entre chaque occurrence", verbose_name='Nombre de mois')),
                ('nombre_par_an', models.PositiveSmallIntegerField(default=12, help_text="Nombre de fois par an (12=mensuel, 4=trimestriel, etc.)", verbose_name='Occurrences par an')),
                ('ordre', models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'db_table': 'periodicites',
                'verbose_name': 'Périodicité',
                'verbose_name_plural': 'Périodicités',
                'ordering': ['ordre', 'nombre_mois'],
            },
        ),

        # 2. Créer la table TypeMandat
        migrations.CreateModel(
            name='TypeMandat',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='Code unique (ex: COMPTA, TVA, SALAIRES)', max_length=30, unique=True, verbose_name='Code')),
                ('libelle', models.CharField(max_length=100, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('icone', models.CharField(blank=True, default='ph-briefcase', help_text="Classe CSS de l'icône (Phosphor Icons)", max_length=50, verbose_name='Icône')),
                ('couleur', models.CharField(blank=True, default='primary', help_text='Classe Bootstrap (primary, success, warning, etc.)', max_length=20, verbose_name='Couleur')),
                ('modules_actifs', models.JSONField(blank=True, default=list, help_text='Liste des modules activés par défaut: ["compta", "tva", "salaires"]', verbose_name='Modules actifs')),
                ('ordre', models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
                ('periodicite_defaut', models.ForeignKey(blank=True, help_text='Périodicité suggérée par défaut pour ce type de mandat', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.periodicite', verbose_name='Périodicité par défaut')),
            ],
            options={
                'db_table': 'types_mandats',
                'verbose_name': 'Type de mandat',
                'verbose_name_plural': 'Types de mandats',
                'ordering': ['ordre', 'libelle'],
            },
        ),

        # 3. Créer la table TypeFacturation
        migrations.CreateModel(
            name='TypeFacturation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='Code unique (ex: FORFAIT, HORAIRE, MIXTE)', max_length=30, unique=True, verbose_name='Code')),
                ('libelle', models.CharField(max_length=100, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('necessite_forfait', models.BooleanField(default=False, help_text='Si coché, le montant forfaitaire est obligatoire', verbose_name='Nécessite un montant forfait')),
                ('necessite_taux_horaire', models.BooleanField(default=False, help_text='Si coché, le taux horaire est obligatoire', verbose_name='Nécessite un taux horaire')),
                ('ordre', models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'db_table': 'types_facturation',
                'verbose_name': 'Type de facturation',
                'verbose_name_plural': 'Types de facturation',
                'ordering': ['ordre', 'libelle'],
            },
        ),

        # 4. Ajouter les nouveaux champs ForeignKey au Mandat
        migrations.AddField(
            model_name='mandat',
            name='type_mandat_ref',
            field=models.ForeignKey(
                blank=True,
                help_text='Type de mandat (nouvelle table)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='core.typemandat',
                verbose_name='Type de mandat'
            ),
        ),
        migrations.AddField(
            model_name='mandat',
            name='periodicite_ref',
            field=models.ForeignKey(
                blank=True,
                help_text='Périodicité (nouvelle table)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='core.periodicite',
                verbose_name='Périodicité'
            ),
        ),
        migrations.AddField(
            model_name='mandat',
            name='type_facturation_ref',
            field=models.ForeignKey(
                blank=True,
                help_text='Type de facturation (nouvelle table)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='core.typefacturation',
                verbose_name='Type de facturation'
            ),
        ),

        # 5. Modifier les anciens champs pour les rendre optionnels (compatibilité)
        migrations.AlterField(
            model_name='mandat',
            name='type_mandat',
            field=models.CharField(
                blank=True,
                choices=[
                    ('COMPTA', 'Comptabilité'),
                    ('TVA', 'TVA'),
                    ('SALAIRES', 'Salaires'),
                    ('FISCAL', 'Conseil fiscal'),
                    ('REVISION', 'Révision'),
                    ('CONSEIL', 'Conseil général'),
                    ('CREATION', 'Création entreprise'),
                    ('GLOBAL', 'Mandat global'),
                ],
                db_index=True,
                max_length=20,
                verbose_name='Type de mandat (ancien)'
            ),
        ),
        migrations.AlterField(
            model_name='mandat',
            name='periodicite',
            field=models.CharField(
                blank=True,
                choices=[
                    ('MENSUEL', 'Mensuel'),
                    ('TRIMESTRIEL', 'Trimestriel'),
                    ('SEMESTRIEL', 'Semestriel'),
                    ('ANNUEL', 'Annuel'),
                    ('PONCTUEL', 'Ponctuel'),
                ],
                max_length=20,
                verbose_name='Périodicité (ancien)'
            ),
        ),
        migrations.AlterField(
            model_name='mandat',
            name='type_facturation',
            field=models.CharField(
                blank=True,
                choices=[
                    ('FORFAIT', 'Forfait'),
                    ('HORAIRE', 'Taux horaire'),
                    ('MIXTE', 'Mixte'),
                ],
                default='HORAIRE',
                max_length=20,
                verbose_name='Type de facturation (ancien)'
            ),
        ),

        # 6. Insérer les données initiales
        migrations.RunPython(create_initial_periodicites, migrations.RunPython.noop),
        migrations.RunPython(create_initial_types_mandats, migrations.RunPython.noop),
        migrations.RunPython(create_initial_types_facturation, migrations.RunPython.noop),

        # 7. Migrer les données existantes des mandats
        migrations.RunPython(migrate_existing_mandats, reverse_migrate_mandats),
    ]
