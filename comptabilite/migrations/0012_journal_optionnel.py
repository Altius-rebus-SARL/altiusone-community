# Generated manually on 2026-01-07
"""
Migration pour rendre le champ journal optionnel dans PieceComptable.

Certains mandats n'ont pas de journaux configurés, donc le journal
doit être optionnel pour permettre la création de pièces comptables.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0011_type_piece_comptable'),
    ]

    operations = [
        # 1. Rendre le champ journal nullable
        migrations.AlterField(
            model_name='piececomptable',
            name='journal',
            field=models.ForeignKey(
                blank=True,
                help_text="Journal comptable (optionnel si le mandat n'en a pas)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pieces',
                to='comptabilite.journal',
            ),
        ),

        # 2. Supprimer la contrainte unique_together qui incluait journal
        migrations.AlterUniqueTogether(
            name='piececomptable',
            unique_together=set(),
        ),

        # 3. Ajouter une contrainte unique sur mandat + numero_piece seulement
        # (le numéro de pièce doit être unique par mandat)
        migrations.AddConstraint(
            model_name='piececomptable',
            constraint=models.UniqueConstraint(
                fields=['mandat', 'numero_piece'],
                name='unique_numero_piece_par_mandat'
            ),
        ),
    ]
