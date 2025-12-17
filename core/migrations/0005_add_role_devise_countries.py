# Generated manually
import django.core.validators
import django.db.models.deletion
import django_countries.fields
import uuid
from django.db import migrations, models


def copy_role_to_legacy(apps, schema_editor):
    """Copie les valeurs de role (CharField) vers role_legacy avant modification"""
    from django.db import connection
    with connection.cursor() as cursor:
        # Vérifier si la colonne role existe et est de type varchar
        cursor.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'role'
        """)
        result = cursor.fetchone()
        if result and result[0] in ('character varying', 'varchar', 'text'):
            # Ajouter la colonne role_legacy si elle n'existe pas
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS role_legacy VARCHAR(20)
            """)
            # Copier les données
            cursor.execute("""
                UPDATE users SET role_legacy = role WHERE role_legacy IS NULL
            """)


def create_initial_roles(apps, schema_editor):
    """Crée les rôles initiaux"""
    Role = apps.get_model('core', 'Role')

    roles_data = [
        {'code': 'ADMIN', 'nom': 'Administrateur', 'niveau': 100, 'description': 'Accès complet à toutes les fonctionnalités'},
        {'code': 'MANAGER', 'nom': 'Chef de bureau', 'niveau': 80, 'description': 'Gestion des mandats et supervision'},
        {'code': 'COMPTABLE', 'nom': 'Comptable', 'niveau': 60, 'description': 'Comptabilité et facturation'},
        {'code': 'ASSISTANT', 'nom': 'Assistant', 'niveau': 40, 'description': 'Tâches administratives de base'},
        {'code': 'CLIENT', 'nom': 'Client', 'niveau': 10, 'description': 'Accès limité au portail client'},
    ]

    for i, role_data in enumerate(roles_data):
        Role.objects.get_or_create(
            code=role_data['code'],
            defaults={
                'nom': role_data['nom'],
                'niveau': role_data['niveau'],
                'description': role_data['description'],
                'est_role_defaut': role_data['code'] == 'ASSISTANT',
                'actif': True,
            }
        )


def create_initial_devises(apps, schema_editor):
    """Crée les devises initiales"""
    Devise = apps.get_model('core', 'Devise')

    devises_data = [
        {'code': 'CHF', 'nom': 'Franc suisse', 'symbole': 'CHF', 'est_devise_base': True},
        {'code': 'EUR', 'nom': 'Euro', 'symbole': '€', 'taux_change': 1.05},
        {'code': 'USD', 'nom': 'Dollar américain', 'symbole': '$', 'symbole_avant': True, 'taux_change': 1.12},
        {'code': 'GBP', 'nom': 'Livre sterling', 'symbole': '£', 'symbole_avant': True, 'taux_change': 0.89},
    ]

    for devise_data in devises_data:
        code = devise_data.pop('code')
        Devise.objects.get_or_create(code=code, defaults=devise_data)


def migrate_user_roles(apps, schema_editor):
    """Migre les utilisateurs vers le nouveau système de rôles"""
    Role = apps.get_model('core', 'Role')
    User = apps.get_model('core', 'User')

    role_map = {r.code: r for r in Role.objects.all()}

    for user in User.objects.all():
        if hasattr(user, 'role_legacy') and user.role_legacy:
            if user.role_legacy in role_map:
                user.role = role_map[user.role_legacy]
                user.save()


def reverse_roles(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    Role.objects.all().delete()


def reverse_devises(apps, schema_editor):
    Devise = apps.get_model('core', 'Devise')
    Devise.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0004_add_compte_bancaire'),
    ]

    operations = [
        # 1. Créer les nouveaux modèles
        migrations.CreateModel(
            name='Devise',
            fields=[
                ('code', models.CharField(help_text='Code ISO 4217 (ex: CHF, EUR, USD)', max_length=3, primary_key=True, serialize=False, verbose_name='Code ISO')),
                ('nom', models.CharField(max_length=50, verbose_name='Nom')),
                ('symbole', models.CharField(help_text='Ex: Fr., €, $', max_length=5, verbose_name='Symbole')),
                ('decimales', models.PositiveSmallIntegerField(default=2, validators=[django.core.validators.MaxValueValidator(4)], verbose_name='Décimales')),
                ('separateur_milliers', models.CharField(default="'", max_length=1, verbose_name='Séparateur milliers')),
                ('separateur_decimal', models.CharField(default='.', max_length=1, verbose_name='Séparateur décimal')),
                ('symbole_avant', models.BooleanField(default=False, verbose_name='Symbole avant le montant')),
                ('taux_change', models.DecimalField(decimal_places=6, default=1, max_digits=12, verbose_name='Taux de change')),
                ('date_taux', models.DateField(blank=True, null=True, verbose_name='Date du taux')),
                ('est_devise_base', models.BooleanField(default=False, verbose_name='Devise de base')),
                ('actif', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'verbose_name': 'Devise',
                'verbose_name_plural': 'Devises',
                'db_table': 'devises',
                'ordering': ['-est_devise_base', 'code'],
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=30, unique=True, verbose_name='Code')),
                ('nom', models.CharField(max_length=100, verbose_name='Nom')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('niveau', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Niveau hiérarchique')),
                ('permissions_custom', models.JSONField(blank=True, default=list, verbose_name='Permissions personnalisées')),
                ('peut_etre_assigne', models.BooleanField(default=True, verbose_name='Peut être assigné')),
                ('est_role_defaut', models.BooleanField(default=False, verbose_name='Rôle par défaut')),
                ('actif', models.BooleanField(default=True, verbose_name='Actif')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('permissions', models.ManyToManyField(blank=True, to='auth.permission', verbose_name='Permissions')),
            ],
            options={
                'verbose_name': 'Rôle',
                'verbose_name_plural': 'Rôles',
                'db_table': 'roles',
                'ordering': ['-niveau', 'nom'],
            },
        ),

        # 2. Sauvegarder role dans role_legacy
        migrations.RunPython(copy_role_to_legacy, migrations.RunPython.noop),

        # 3. Supprimer l'ancien champ role (CharField)
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),

        # 4. Ajouter le nouveau champ role (ForeignKey)
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='utilisateurs', to='core.role', verbose_name='Rôle'),
        ),

        # 5. Créer les rôles et devises initiaux
        migrations.RunPython(create_initial_roles, reverse_roles),
        migrations.RunPython(create_initial_devises, reverse_devises),

        # 6. Migrer les utilisateurs
        migrations.RunPython(migrate_user_roles, migrations.RunPython.noop),

        # 7. Modifier les adresses
        migrations.RenameField(
            model_name='adresse',
            old_name='npa',
            new_name='code_postal',
        ),
        migrations.AlterField(
            model_name='adresse',
            name='code_postal',
            field=models.CharField(default='', max_length=20, verbose_name='Code postal'),
        ),
        migrations.AddField(
            model_name='adresse',
            name='region',
            field=models.CharField(blank=True, max_length=100, verbose_name='Région/Canton/État'),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='canton',
            field=models.CharField(blank=True, choices=[('AG', 'Argovie'), ('AI', 'Appenzell Rhodes-Intérieures'), ('AR', 'Appenzell Rhodes-Extérieures'), ('BE', 'Berne'), ('BL', 'Bâle-Campagne'), ('BS', 'Bâle-Ville'), ('FR', 'Fribourg'), ('GE', 'Genève'), ('GL', 'Glaris'), ('GR', 'Grisons'), ('JU', 'Jura'), ('LU', 'Lucerne'), ('NE', 'Neuchâtel'), ('NW', 'Nidwald'), ('OW', 'Obwald'), ('SG', 'Saint-Gall'), ('SH', 'Schaffhouse'), ('SO', 'Soleure'), ('SZ', 'Schwyz'), ('TG', 'Thurgovie'), ('TI', 'Tessin'), ('UR', 'Uri'), ('VD', 'Vaud'), ('VS', 'Valais'), ('ZG', 'Zoug'), ('ZH', 'Zurich')], max_length=2, verbose_name='Canton'),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='pays',
            field=django_countries.fields.CountryField(default='CH', max_length=2, verbose_name='Pays'),
        ),
    ]
