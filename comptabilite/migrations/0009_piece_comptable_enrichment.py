# comptabilite/migrations/0009_piece_comptable_enrichment.py
"""
Migration pour enrichir le modèle PieceComptable:
- Ajout du type de pièce
- Lien ManyToMany vers documents justificatifs
- Lien FK vers dossier de classement
- Métadonnées OCR
- Informations tiers et montants
- Lien FK de EcritureComptable vers PieceComptable
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0008_rename_conv_user_statut_idx_conversatio_utilisa_adc1dd_idx_and_more'),
        ('comptabilite', '0008_alter_compte_options_alter_ecriturecomptable_options_and_more'),
    ]

    operations = [
        # 1. Modifier numero_piece pour ne plus être unique globalement
        migrations.AlterField(
            model_name='piececomptable',
            name='numero_piece',
            field=models.CharField(db_index=True, max_length=50),
        ),

        # 2. Ajouter type_piece
        migrations.AddField(
            model_name='piececomptable',
            name='type_piece',
            field=models.CharField(
                choices=[
                    ('FACTURE_ACHAT', "Facture d'achat"),
                    ('FACTURE_VENTE', 'Facture de vente'),
                    ('NOTE_FRAIS', 'Note de frais'),
                    ('RELEVE_BANQUE', 'Relevé bancaire'),
                    ('CAISSE', 'Pièce de caisse'),
                    ('OD', 'Opération diverse'),
                    ('AVOIR', 'Avoir'),
                    ('SALAIRE', 'Fiche de salaire'),
                    ('AUTRE', 'Autre'),
                ],
                db_index=True,
                default='AUTRE',
                max_length=20,
            ),
        ),

        # 3. Ajouter documents_justificatifs (ManyToMany)
        migrations.AddField(
            model_name='piececomptable',
            name='documents_justificatifs',
            field=models.ManyToManyField(
                blank=True,
                help_text='Documents justificatifs attachés à cette pièce',
                related_name='pieces_comptables',
                to='documents.document',
            ),
        ),

        # 4. Ajouter dossier FK
        migrations.AddField(
            model_name='piececomptable',
            name='dossier',
            field=models.ForeignKey(
                blank=True,
                help_text='Dossier de classement des justificatifs',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pieces_comptables',
                to='documents.dossier',
            ),
        ),

        # 5. Ajouter metadata_ocr
        migrations.AddField(
            model_name='piececomptable',
            name='metadata_ocr',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Métadonnées extraites automatiquement par OCR',
            ),
        ),

        # 6. Ajouter reference_externe
        migrations.AddField(
            model_name='piececomptable',
            name='reference_externe',
            field=models.CharField(
                blank=True,
                help_text='Référence externe (ex: numéro facture fournisseur)',
                max_length=100,
            ),
        ),

        # 7. Ajouter tiers_nom
        migrations.AddField(
            model_name='piececomptable',
            name='tiers_nom',
            field=models.CharField(blank=True, max_length=200),
        ),

        # 8. Ajouter tiers_numero_tva
        migrations.AddField(
            model_name='piececomptable',
            name='tiers_numero_tva',
            field=models.CharField(blank=True, max_length=50),
        ),

        # 9. Ajouter montant_ht
        migrations.AddField(
            model_name='piececomptable',
            name='montant_ht',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),

        # 10. Ajouter montant_tva
        migrations.AddField(
            model_name='piececomptable',
            name='montant_tva',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),

        # 11. Ajouter montant_ttc
        migrations.AddField(
            model_name='piececomptable',
            name='montant_ttc',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),

        # 12. Ajouter valide_par
        migrations.AddField(
            model_name='piececomptable',
            name='valide_par',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pieces_validees',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 13. Ajouter date_validation
        migrations.AddField(
            model_name='piececomptable',
            name='date_validation',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # 14. Ajouter contrainte unique_together
        migrations.AlterUniqueTogether(
            name='piececomptable',
            unique_together={('mandat', 'journal', 'numero_piece')},
        ),

        # 15. Ajouter index pour type_piece et statut
        migrations.AddIndex(
            model_name='piececomptable',
            index=models.Index(
                fields=['type_piece', 'statut'],
                name='pieces_comp_type_pi_idx',
            ),
        ),

        # 16. Modifier les related_name de mandat et journal
        migrations.AlterField(
            model_name='piececomptable',
            name='mandat',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pieces_comptables',
                to='core.mandat',
            ),
        ),
        migrations.AlterField(
            model_name='piececomptable',
            name='journal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pieces',
                to='comptabilite.journal',
            ),
        ),

        # 17. Ajouter FK piece sur EcritureComptable
        migrations.AddField(
            model_name='ecriturecomptable',
            name='piece',
            field=models.ForeignKey(
                blank=True,
                help_text='Pièce comptable regroupant les écritures',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ecritures',
                to='comptabilite.piececomptable',
            ),
        ),
    ]
