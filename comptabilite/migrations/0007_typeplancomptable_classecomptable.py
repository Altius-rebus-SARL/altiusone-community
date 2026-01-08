# Generated manually - Migration for TypePlanComptable and ClasseComptable

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def create_type_plans_and_migrate_data(apps, schema_editor):
    """
    Crée les types de plans comptables et migre les données existantes.
    """
    TypePlanComptable = apps.get_model('comptabilite', 'TypePlanComptable')
    ClasseComptable = apps.get_model('comptabilite', 'ClasseComptable')
    PlanComptable = apps.get_model('comptabilite', 'PlanComptable')

    # Définition des types de plans comptables
    types_plans = {
        'PME': {
            'nom': 'Plan Comptable PME Suisse',
            'description': 'Plan comptable standard pour les PME suisses selon le Code des obligations',
            'pays': 'Suisse',
            'region': 'Europe',
            'norme_comptable': 'CO (Code des obligations)',
            'version': '2023',
            'ordre': 1,
            'classes': [
                {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Produits d\'exploitation', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Charges de matériel', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Autres charges d\'exploitation', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Résultats des activités annexes', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Résultats extraordinaires', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
            ]
        },
        'OHADA': {
            'nom': 'Plan Comptable OHADA',
            'description': 'Système comptable OHADA pour les pays de la zone OHADA',
            'pays': 'Zone OHADA',
            'region': 'Afrique',
            'norme_comptable': 'SYSCOHADA révisé',
            'version': '2017',
            'ordre': 2,
            'classes': [
                {'numero': 1, 'libelle': 'Comptes de ressources durables', 'type_compte': 'PASSIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Comptes d\'actif immobilisé', 'type_compte': 'ACTIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Comptes de stocks', 'type_compte': 'ACTIF', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Comptes de tiers', 'type_compte': 'ACTIF', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Comptes de trésorerie', 'type_compte': 'ACTIF', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Comptes de charges des activités ordinaires', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Comptes de produits des activités ordinaires', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Comptes des autres charges et produits', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
            ]
        },
        'SWISSGAAP': {
            'nom': 'Plan Comptable Swiss GAAP RPC',
            'description': 'Plan comptable selon les recommandations relatives à la présentation des comptes (Swiss GAAP RPC)',
            'pays': 'Suisse',
            'region': 'Europe',
            'norme_comptable': 'Swiss GAAP RPC',
            'version': '2023',
            'ordre': 3,
            'classes': [
                {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Produits d\'exploitation', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Charges de matériel', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Autres charges d\'exploitation', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Résultats des activités annexes', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Résultats extraordinaires', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
            ]
        },
        'GENERAL': {
            'nom': 'Plan Comptable Général',
            'description': 'Plan comptable général standard',
            'pays': '',
            'region': '',
            'norme_comptable': 'Standard',
            'version': '2023',
            'ordre': 4,
            'classes': [
                {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Produits', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Autres charges', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Autres produits', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Résultats', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
            ]
        },
        'ENTREPRISE': {
            'nom': 'Plan Comptable Entreprise',
            'description': 'Plan comptable pour grandes entreprises',
            'pays': '',
            'region': '',
            'norme_comptable': 'Standard',
            'version': '2023',
            'ordre': 5,
            'classes': [
                {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Produits', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Autres charges', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Autres produits', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Résultats', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
            ]
        },
        'PERSONNALISE': {
            'nom': 'Plan Comptable Personnalisé',
            'description': 'Plan comptable personnalisé',
            'pays': '',
            'region': '',
            'norme_comptable': 'Personnalisé',
            'version': '',
            'ordre': 99,
            'classes': [
                {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Produits', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Produits', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Résultats', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
            ]
        },
    }

    # Créer les types de plans et leurs classes
    type_plan_map = {}  # code -> TypePlanComptable instance
    for code, data in types_plans.items():
        type_plan = TypePlanComptable.objects.create(
            id=uuid.uuid4(),
            code=code,
            nom=data['nom'],
            description=data['description'],
            pays=data['pays'],
            region=data['region'],
            norme_comptable=data['norme_comptable'],
            version=data['version'],
            ordre=data['ordre'],
            is_active=True,
        )
        type_plan_map[code] = type_plan

        # Créer les classes pour ce type
        for classe_data in data['classes']:
            ClasseComptable.objects.create(
                id=uuid.uuid4(),
                type_plan=type_plan,
                numero=classe_data['numero'],
                libelle=classe_data['libelle'],
                type_compte=classe_data['type_compte'],
                numero_debut=classe_data['numero_debut'],
                numero_fin=classe_data['numero_fin'],
                is_active=True,
            )

    # Migrer les plans comptables existants
    for plan in PlanComptable.objects.all():
        old_type = plan.type_plan_old
        if old_type in type_plan_map:
            plan.type_plan = type_plan_map[old_type]
            plan.save()


def reverse_migration(apps, schema_editor):
    """
    Reverse: recopie le code du type vers type_plan_old
    """
    PlanComptable = apps.get_model('comptabilite', 'PlanComptable')
    for plan in PlanComptable.objects.select_related('type_plan').all():
        if plan.type_plan:
            plan.type_plan_old = plan.type_plan.code
            plan.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('comptabilite', '0006_alter_plancomptable_type_plan'),
    ]

    operations = [
        # 1. Créer la table TypePlanComptable
        migrations.CreateModel(
            name='TypePlanComptable',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('code', models.CharField(db_index=True, help_text='Code unique (PME, OHADA, SWISSGAAP, etc.)', max_length=20, unique=True)),
                ('nom', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('pays', models.CharField(blank=True, help_text="Pays d'application (Suisse, Zone OHADA, etc.)", max_length=100)),
                ('region', models.CharField(blank=True, help_text='Région ou zone économique', max_length=100)),
                ('norme_comptable', models.CharField(blank=True, help_text='Norme comptable de référence (CO, OHADA, IFRS, etc.)', max_length=100)),
                ('version', models.CharField(blank=True, help_text='Version du plan', max_length=20)),
                ('date_publication', models.DateField(blank=True, null=True)),
                ('ordre', models.IntegerField(default=0, help_text="Ordre d'affichage dans les listes")),
            ],
            options={
                'db_table': 'types_plans_comptables',
                'verbose_name': 'Type de plan comptable',
                'verbose_name_plural': 'Types de plans comptables',
                'ordering': ['ordre', 'code'],
            },
        ),

        # 2. Créer la table ClasseComptable
        migrations.CreateModel(
            name='ClasseComptable',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('type_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='comptabilite.typeplancomptable')),
                ('numero', models.IntegerField(help_text='Numéro de la classe (1, 2, 3...)')),
                ('libelle', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('type_compte', models.CharField(choices=[('ACTIF', 'Actif'), ('PASSIF', 'Passif'), ('CHARGE', 'Charge'), ('PRODUIT', 'Produit'), ('RESULTAT', 'Résultat')], help_text='Nature des comptes de cette classe', max_length=10)),
                ('numero_debut', models.CharField(blank=True, help_text='Premier numéro de compte (ex: 1000)', max_length=10)),
                ('numero_fin', models.CharField(blank=True, help_text='Dernier numéro de compte (ex: 1999)', max_length=10)),
            ],
            options={
                'db_table': 'classes_comptables',
                'verbose_name': 'Classe comptable',
                'verbose_name_plural': 'Classes comptables',
                'ordering': ['type_plan', 'numero'],
                'unique_together': {('type_plan', 'numero')},
            },
        ),

        # 3. Renommer l'ancien champ type_plan en type_plan_old
        migrations.RenameField(
            model_name='plancomptable',
            old_name='type_plan',
            new_name='type_plan_old',
        ),

        # 4. Ajouter le nouveau champ FK type_plan (nullable temporairement)
        migrations.AddField(
            model_name='plancomptable',
            name='type_plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Type de plan comptable (PME, OHADA, etc.)',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='plans',
                to='comptabilite.typeplancomptable'
            ),
        ),

        # 5. Ajouter le champ classe_comptable au modèle Compte
        migrations.AddField(
            model_name='compte',
            name='classe_comptable',
            field=models.ForeignKey(
                blank=True,
                help_text='Classe comptable de référence',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='comptes',
                to='comptabilite.classecomptable'
            ),
        ),

        # 6. Exécuter la migration de données
        migrations.RunPython(create_type_plans_and_migrate_data, reverse_migration),

        # 7. Rendre le champ type_plan non nullable
        migrations.AlterField(
            model_name='plancomptable',
            name='type_plan',
            field=models.ForeignKey(
                help_text='Type de plan comptable (PME, OHADA, etc.)',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='plans',
                to='comptabilite.typeplancomptable'
            ),
        ),

        # 8. Supprimer l'ancien champ type_plan_old
        migrations.RemoveField(
            model_name='plancomptable',
            name='type_plan_old',
        ),
    ]
