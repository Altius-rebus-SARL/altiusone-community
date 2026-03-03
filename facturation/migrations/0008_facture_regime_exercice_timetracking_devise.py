# facturation/migrations/0008_facture_regime_exercice_timetracking_devise.py
"""
Add regime_fiscal and exercice FK to Facture.
Add devise FK to TimeTracking.
Change default of Prestation.taux_tva_defaut and LigneFacture.taux_tva from 8.1 to 0.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0007_prestation_taux_tva_ref'),
        ('tva', '0006_declarationtva_regime_devise_operationtva_fk'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        # Facture: add regime_fiscal FK
        migrations.AddField(
            model_name='facture',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal applicable à cette facture',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='factures',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
        # Facture: add exercice FK
        migrations.AddField(
            model_name='facture',
            name='exercice',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Exercice comptable de rattachement',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='factures',
                to='core.exercicecomptable',
                verbose_name='Exercice comptable',
            ),
        ),
        # TimeTracking: add devise FK
        migrations.AddField(
            model_name='timetracking',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Devise du taux horaire et du montant',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='temps_travail',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        # Prestation: change default from 8.1 to 0
        migrations.AlterField(
            model_name='prestation',
            name='taux_tva_defaut',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=5,
                help_text='Taux de TVA appliqué par défaut (résolu depuis le régime fiscal si 0)',
                verbose_name='Taux TVA par défaut',
            ),
        ),
        # LigneFacture: change default from 8.1 to 0
        migrations.AlterField(
            model_name='lignefacture',
            name='taux_tva',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=5,
                help_text='Taux de TVA appliqué (résolu depuis le régime fiscal du mandat)',
                verbose_name='Taux TVA',
            ),
        ),
    ]
