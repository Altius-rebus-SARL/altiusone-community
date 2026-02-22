# comptabilite/migrations/0004_ecriturecomptable_piececomptable_tiers.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0003_alter_ecriturecomptable_devise'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='ecriturecomptable',
            name='code_tva_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ecritures_comptables',
                to='tva.codetva',
                verbose_name='Code TVA (référence)',
                help_text='Référence structurée vers le code TVA du régime fiscal',
            ),
        ),
        migrations.AddField(
            model_name='ecriturecomptable',
            name='tiers',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ecritures_comptables',
                to='core.tiers',
                verbose_name='Tiers',
                help_text='Tiers associé à cette écriture',
            ),
        ),
        migrations.AddField(
            model_name='piececomptable',
            name='tiers',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pieces_comptables',
                to='core.tiers',
                verbose_name='Tiers (référence)',
                help_text='Référence structurée vers le tiers centralisé',
            ),
        ),
    ]
