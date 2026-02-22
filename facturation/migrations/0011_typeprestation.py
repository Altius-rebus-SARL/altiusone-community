import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0010_alter_paiement_devise_alter_tarifmandat_devise'),
    ]

    operations = [
        # 1. Create TypePrestation table
        migrations.CreateModel(
            name='TypePrestation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=30, unique=True, verbose_name='Code')),
                ('libelle', models.CharField(max_length=100, verbose_name='Libellé')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('icone', models.CharField(blank=True, default='ph-package', max_length=50, verbose_name='Icône')),
                ('couleur', models.CharField(blank=True, default='primary', max_length=20, verbose_name='Couleur')),
                ('ordre', models.PositiveSmallIntegerField(default=0, verbose_name='Ordre')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'db_table': 'types_prestations',
                'ordering': ['ordre', 'libelle'],
                'verbose_name': 'Type de prestation',
                'verbose_name_plural': 'Types de prestations',
            },
        ),
        # 2. Add nullable FK type_prestation_ref on Prestation
        migrations.AddField(
            model_name='prestation',
            name='type_prestation_ref',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='prestations_temp',
                to='facturation.typeprestation',
                verbose_name='Type de prestation',
                help_text='Catégorie de la prestation',
            ),
        ),
        # 3. Make old CharField blank=True for transition
        migrations.AlterField(
            model_name='prestation',
            name='type_prestation',
            field=models.CharField(
                blank=True, max_length=20,
                verbose_name='Type de prestation (ancien)',
                help_text='Catégorie de la prestation (ancien champ)',
            ),
        ),
    ]
