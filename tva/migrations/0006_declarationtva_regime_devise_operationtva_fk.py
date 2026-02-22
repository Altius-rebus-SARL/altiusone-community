# tva/migrations/0006_declarationtva_regime_devise_operationtva_fk.py
"""
Add regime_fiscal and devise FK to DeclarationTVA.
Add facture and tiers_ref FK to OperationTVA.
All nullable for now, populated in 0007.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
        ('core', '0007_mandat_regime_devise_not_null'),
        ('facturation', '0007_prestation_taux_tva_ref'),
    ]

    operations = [
        # DeclarationTVA: add regime_fiscal FK
        migrations.AddField(
            model_name='declarationtva',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal applicable à cette déclaration',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_tva',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
        # DeclarationTVA: add devise FK
        migrations.AddField(
            model_name='declarationtva',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Devise de la déclaration TVA',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_tva',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        # OperationTVA: add facture FK
        migrations.AddField(
            model_name='operationtva',
            name='facture',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Facture liée à cette opération TVA',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='operations_tva',
                to='facturation.facture',
                verbose_name='Facture',
            ),
        ),
        # OperationTVA: add tiers_ref FK
        migrations.AddField(
            model_name='operationtva',
            name='tiers_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Référence structurée vers le tiers centralisé',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='operations_tva',
                to='core.tiers',
                verbose_name='Tiers (référence)',
            ),
        ),
    ]
