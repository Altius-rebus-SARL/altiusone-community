# comptabilite/migrations/0006_plancomptable_devise_journal_devise_piece_devise_compte_codetva.py
"""
Add devise FK to PlanComptable, Journal, PieceComptable.
Add code_tva_defaut_ref FK to Compte.
All nullable.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0005_populate_code_tva_ref'),
        ('core', '0007_mandat_regime_devise_not_null'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        # PlanComptable: add devise FK
        migrations.AddField(
            model_name='plancomptable',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Devise dans laquelle sont exprimés les soldes de ce plan',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='plans_comptables',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        # Journal: add devise FK
        migrations.AddField(
            model_name='journal',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Devise de référence du journal (vide si multi-devise)',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='journaux',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        # PieceComptable: add devise FK
        migrations.AddField(
            model_name='piececomptable',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Devise des montants de cette pièce',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pieces_comptables',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        # Compte: add code_tva_defaut_ref FK
        migrations.AddField(
            model_name='compte',
            name='code_tva_defaut_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Référence structurée vers le code TVA du régime fiscal',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='comptes_defaut',
                to='tva.codetva',
                verbose_name='Code TVA par défaut (référence)',
            ),
        ),
    ]
