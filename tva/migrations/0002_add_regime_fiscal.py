# tva/migrations/0002_add_regime_fiscal.py
# Schema migration: create RegimeFiscal, add regime FK to TauxTVA/CodeTVA/ConfigurationTVA

import django.db.models.deletion
import django_countries.fields
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0001_initial'),
        ('core', '0001_initial'),
        ('comptabilite', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create RegimeFiscal model
        migrations.CreateModel(
            name='RegimeFiscal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('code', models.CharField(help_text='Code du regime (ex: CH, CM, SN, CI)', max_length=20, unique=True, verbose_name='Code')),
                ('nom', models.CharField(help_text='Nom du regime fiscal (ex: Suisse, Cameroun OHADA)', max_length=200, verbose_name='Nom')),
                ('pays', django_countries.fields.CountryField(help_text='Pays du regime fiscal', max_length=2, verbose_name='Pays')),
                ('nom_taxe', models.CharField(default='TVA', help_text='Nom local de la taxe (TVA, VAT, IVA)', max_length=50, verbose_name='Nom de la taxe')),
                ('taux_normal', models.DecimalField(decimal_places=2, help_text='Taux normal de la taxe en %', max_digits=5, verbose_name='Taux normal')),
                ('a_taux_reduit', models.BooleanField(default=False, help_text='Le regime propose-t-il un taux réduit ?', verbose_name='A un taux réduit')),
                ('a_taux_special', models.BooleanField(default=False, help_text='Le regime propose-t-il un taux spécial ?', verbose_name='A un taux spécial')),
                ('format_numero_tva', models.CharField(blank=True, help_text='Expression régulière de validation du numéro TVA', max_length=255, verbose_name='Format numéro TVA')),
                ('supporte_xml', models.BooleanField(default=False, help_text="Seul le regime suisse supporte actuellement l'export XML AFC", verbose_name='Supporte export XML')),
                ('methodes_disponibles', models.JSONField(default=list, help_text='Liste des méthodes de calcul disponibles pour ce regime', verbose_name='Méthodes disponibles')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('devise_defaut', models.ForeignKey(help_text='Devise utilisée par défaut pour ce regime', on_delete=django.db.models.deletion.PROTECT, to='core.devise', verbose_name='Devise par défaut')),
                ('type_plan_comptable', models.ForeignKey(blank=True, help_text='Plan comptable associé à ce regime', null=True, on_delete=django.db.models.deletion.SET_NULL, to='comptabilite.typeplancomptable', verbose_name='Type de plan comptable')),
            ],
            options={
                'verbose_name': 'Régime fiscal',
                'verbose_name_plural': 'Régimes fiscaux',
                'db_table': 'regimes_fiscaux',
                'ordering': ['code'],
            },
        ),

        # 2. Add regime FK to TauxTVA (nullable for now)
        migrations.AddField(
            model_name='tauxtva',
            name='regime',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal auquel appartient ce taux',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='taux',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),

        # 3. Add EXONERE to TauxTVA.TYPE_CHOICES
        migrations.AlterField(
            model_name='tauxtva',
            name='type_taux',
            field=models.CharField(
                choices=[('NORMAL', 'Taux normal'), ('REDUIT', 'Taux réduit'), ('SPECIAL', 'Taux spécial hébergement'), ('EXONERE', 'Exonéré')],
                help_text='Catégorie du taux TVA', max_length=10, verbose_name='Type de taux',
            ),
        ),

        # 4. Add regime FK to CodeTVA (nullable for now)
        migrations.AddField(
            model_name='codetva',
            name='regime',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal auquel appartient ce code',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='codes',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),

        # 5. Remove unique=True from CodeTVA.code
        migrations.AlterField(
            model_name='codetva',
            name='code',
            field=models.CharField(db_index=True, help_text='Code du chiffre (ex: 200, 302, 400)', max_length=10, verbose_name='Code'),
        ),

        # 6. Add unique_together on CodeTVA (regime, code)
        migrations.AlterUniqueTogether(
            name='codetva',
            unique_together={('regime', 'code')},
        ),

        # 7. Add regime FK to ConfigurationTVA (nullable, stays nullable)
        migrations.AddField(
            model_name='configurationtva',
            name='regime',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal applicable à ce mandat',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='configurations',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),

        # 8. Extend ConfigurationTVA.METHODE_CHOICES
        migrations.AlterField(
            model_name='configurationtva',
            name='methode_calcul',
            field=models.CharField(
                choices=[
                    ('EFFECTIVE', 'Méthode effective'),
                    ('TAUX_DETTE', 'Méthode des taux de la dette fiscale nette'),
                    ('TAUX_FORFAITAIRE', 'Méthode des taux forfaitaires'),
                    ('FORFAIT_BRANCHE', 'Forfait selon la branche'),
                    ('REEL_NORMAL', 'Régime réel normal'),
                    ('REEL_SIMPLIFIE', 'Régime réel simplifié'),
                    ('FORFAITAIRE', 'Régime forfaitaire'),
                ],
                default='EFFECTIVE',
                help_text='Méthode de décompte TVA utilisée',
                max_length=20,
                verbose_name='Méthode de calcul',
            ),
        ),
    ]
