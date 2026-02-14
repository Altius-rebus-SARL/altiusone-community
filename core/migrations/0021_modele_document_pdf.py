# Generated manually for ModeleDocumentPDF

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_add_parent_client_hierarchy'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModeleDocumentPDF',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('nom', models.CharField(max_length=200, verbose_name='Nom du modèle')),
                ('type_document', models.CharField(
                    choices=[
                        ('FACTURE', 'Facture'),
                        ('AVOIR', 'Avoir'),
                        ('ACOMPTE', "Facture d'acompte"),
                        ('FICHE_SALAIRE', 'Fiche de salaire'),
                        ('CERTIFICAT_SALAIRE', 'Certificat de salaire'),
                        ('CERTIFICAT_TRAVAIL', 'Certificat de travail'),
                        ('DECLARATION_COTISATIONS', 'Déclaration de cotisations'),
                    ],
                    db_index=True,
                    max_length=30,
                    verbose_name='Type de document',
                )),
                ('logo', models.FileField(blank=True, null=True, upload_to='modeles_pdf/logos/', verbose_name='Logo personnalisé')),
                ('utiliser_logo_defaut', models.BooleanField(default=True, verbose_name='Utiliser le logo par défaut')),
                ('couleur_primaire', models.CharField(default='#088178', max_length=7, verbose_name='Couleur primaire')),
                ('couleur_accent', models.CharField(default='#2c3e50', max_length=7, verbose_name='Couleur accent')),
                ('couleur_texte', models.CharField(default='#333333', max_length=7, verbose_name='Couleur du texte')),
                ('police', models.CharField(
                    choices=[
                        ('Helvetica', 'Helvetica'),
                        ('Times-Roman', 'Times Roman'),
                        ('Courier', 'Courier'),
                    ],
                    default='Helvetica',
                    max_length=50,
                    verbose_name='Police',
                )),
                ('marge_haut', models.PositiveIntegerField(default=20, verbose_name='Marge haute (mm)')),
                ('marge_bas', models.PositiveIntegerField(default=25, verbose_name='Marge basse (mm)')),
                ('marge_gauche', models.PositiveIntegerField(default=20, verbose_name='Marge gauche (mm)')),
                ('marge_droite', models.PositiveIntegerField(default=15, verbose_name='Marge droite (mm)')),
                ('textes', models.JSONField(blank=True, default=dict, help_text='Clés: entete, pied_page, introduction, conclusion, conditions, mentions_legales', verbose_name='Textes')),
                ('blocs_visibles', models.JSONField(blank=True, default=dict, help_text='Clés: logo, qr_bill, conditions, introduction, conclusion, etc.', verbose_name='Blocs visibles')),
                ('config', models.JSONField(blank=True, default=dict, verbose_name='Configuration avancée')),
                ('est_defaut', models.BooleanField(default=False, help_text='Un seul modèle par défaut par type et par mandat', verbose_name='Modèle par défaut')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('mandat', models.ForeignKey(blank=True, help_text='Laisser vide pour un modèle système par défaut', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='modeles_pdf', to='core.mandat', verbose_name='Mandat')),
            ],
            options={
                'verbose_name': 'Modèle de document PDF',
                'verbose_name_plural': 'Modèles de document PDF',
                'db_table': 'modeles_document_pdf',
                'ordering': ['type_document', 'nom'],
            },
        ),
        migrations.AddConstraint(
            model_name='modeledocumentpdf',
            constraint=models.UniqueConstraint(
                condition=models.Q(('est_defaut', True)),
                fields=('type_document', 'mandat'),
                name='unique_defaut_par_type_mandat',
            ),
        ),
    ]
