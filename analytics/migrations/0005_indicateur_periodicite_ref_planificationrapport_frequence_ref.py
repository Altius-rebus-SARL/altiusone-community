# Generated manually to add periodicite_ref and frequence_ref
# analytics/migrations/0005_indicateur_periodicite_ref_planificationrapport_frequence_ref.py

from django.db import migrations, models
import django.db.models.deletion


def migrate_indicateurs_periodicite(apps, schema_editor):
    """Migrer les périodicités des indicateurs vers la table de référence"""
    Indicateur = apps.get_model('analytics', 'Indicateur')
    Periodicite = apps.get_model('core', 'Periodicite')

    # Mapping des anciens codes vers les nouveaux
    mapping = {
        'TEMPS_REEL': 'TEMPS_REEL',
        'JOUR': 'JOUR',
        'SEMAINE': 'SEMAINE',
        'MOIS': 'MENSUEL',
        'TRIMESTRE': 'TRIMESTRIEL',
        'ANNEE': 'ANNUEL',
    }

    periodicite_cache = {p.code: p for p in Periodicite.objects.all()}

    for indicateur in Indicateur.objects.all():
        if indicateur.periodicite:
            new_code = mapping.get(indicateur.periodicite, indicateur.periodicite)
            if new_code in periodicite_cache:
                indicateur.periodicite_ref = periodicite_cache[new_code]
                indicateur.save(update_fields=['periodicite_ref'])


def migrate_planifications_frequence(apps, schema_editor):
    """Migrer les fréquences des planifications vers la table de référence"""
    PlanificationRapport = apps.get_model('analytics', 'PlanificationRapport')
    Periodicite = apps.get_model('core', 'Periodicite')

    # Mapping des anciens codes vers les nouveaux
    mapping = {
        'JOUR': 'JOUR',
        'SEMAINE': 'SEMAINE',
        'MOIS': 'MENSUEL',
        'TRIMESTRE': 'TRIMESTRIEL',
        'ANNEE': 'ANNUEL',
    }

    periodicite_cache = {p.code: p for p in Periodicite.objects.all()}

    for planif in PlanificationRapport.objects.all():
        if planif.frequence:
            new_code = mapping.get(planif.frequence, planif.frequence)
            if new_code in periodicite_cache:
                planif.frequence_ref = periodicite_cache[new_code]
                planif.save(update_fields=['frequence_ref'])


def reverse_indicateurs(apps, schema_editor):
    """Reverse migration pour indicateurs"""
    Indicateur = apps.get_model('analytics', 'Indicateur')

    reverse_mapping = {
        'TEMPS_REEL': 'TEMPS_REEL',
        'JOUR': 'JOUR',
        'SEMAINE': 'SEMAINE',
        'MENSUEL': 'MOIS',
        'TRIMESTRIEL': 'TRIMESTRE',
        'ANNUEL': 'ANNEE',
    }

    for indicateur in Indicateur.objects.select_related('periodicite_ref').all():
        if indicateur.periodicite_ref:
            old_code = reverse_mapping.get(indicateur.periodicite_ref.code)
            if old_code:
                indicateur.periodicite = old_code
                indicateur.save(update_fields=['periodicite'])


def reverse_planifications(apps, schema_editor):
    """Reverse migration pour planifications"""
    PlanificationRapport = apps.get_model('analytics', 'PlanificationRapport')

    reverse_mapping = {
        'JOUR': 'JOUR',
        'SEMAINE': 'SEMAINE',
        'MENSUEL': 'MOIS',
        'TRIMESTRIEL': 'TRIMESTRE',
        'ANNUEL': 'ANNEE',
    }

    for planif in PlanificationRapport.objects.select_related('frequence_ref').all():
        if planif.frequence_ref:
            old_code = reverse_mapping.get(planif.frequence_ref.code)
            if old_code:
                planif.frequence = old_code
                planif.save(update_fields=['frequence'])


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0004_alter_alertemetrique_created_at_and_more'),
        ('core', '0009_add_additional_periodicites'),
    ]

    operations = [
        # 1. Ajouter le champ periodicite_ref à Indicateur
        migrations.AddField(
            model_name='indicateur',
            name='periodicite_ref',
            field=models.ForeignKey(
                blank=True,
                help_text="Fréquence de calcul de l'indicateur",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='indicateurs',
                to='core.periodicite',
                verbose_name='Périodicité'
            ),
        ),

        # 2. Modifier l'ancien champ periodicite pour le rendre optionnel
        migrations.AlterField(
            model_name='indicateur',
            name='periodicite',
            field=models.CharField(
                blank=True,
                choices=[
                    ('TEMPS_REEL', 'Temps réel'),
                    ('JOUR', 'Journalier'),
                    ('SEMAINE', 'Hebdomadaire'),
                    ('MOIS', 'Mensuel'),
                    ('TRIMESTRE', 'Trimestriel'),
                    ('ANNEE', 'Annuel'),
                ],
                default='MOIS',
                max_length=20,
                verbose_name='Périodicité (ancien)'
            ),
        ),

        # 3. Ajouter le champ frequence_ref à PlanificationRapport
        migrations.AddField(
            model_name='planificationrapport',
            name='frequence_ref',
            field=models.ForeignKey(
                blank=True,
                help_text='Fréquence de génération du rapport',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='planifications_rapports',
                to='core.periodicite',
                verbose_name='Fréquence'
            ),
        ),

        # 4. Modifier l'ancien champ frequence pour le rendre optionnel
        migrations.AlterField(
            model_name='planificationrapport',
            name='frequence',
            field=models.CharField(
                blank=True,
                choices=[
                    ('JOUR', 'Quotidien'),
                    ('SEMAINE', 'Hebdomadaire'),
                    ('MOIS', 'Mensuel'),
                    ('TRIMESTRE', 'Trimestriel'),
                    ('ANNEE', 'Annuel'),
                ],
                max_length=20,
                verbose_name='Fréquence (ancien)'
            ),
        ),

        # 5. Migrer les données existantes
        migrations.RunPython(migrate_indicateurs_periodicite, reverse_indicateurs),
        migrations.RunPython(migrate_planifications_frequence, reverse_planifications),
    ]
