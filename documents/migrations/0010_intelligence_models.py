# documents/migrations/0010_intelligence_models.py
"""
Add intelligence AI models:
- DocumentRelation: Semantic links between documents
- MandatInsight: Proactive AI-generated insights
- MandatDigest: Periodic AI-generated summaries
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0009_remove_document_path_storage_document_fichier_and_more'),
        ('core', '0016_add_npa_localite_to_client'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # === MandatInsight ===
        migrations.CreateModel(
            name='MandatInsight',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifié le')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
                ('type_insight', models.CharField(
                    choices=[
                        ('ANOMALIE', 'Anomalie détectée'),
                        ('DOUBLON', 'Doublons détectés'),
                        ('MANQUANT', 'Document manquant'),
                        ('TENDANCE', 'Tendance observée'),
                        ('RECOMMANDATION', 'Recommandation'),
                        ('ALERTE', 'Alerte importante'),
                        ('OPPORTUNITE', 'Opportunité'),
                    ],
                    max_length=20,
                    verbose_name="Type d'insight",
                )),
                ('severite', models.CharField(
                    choices=[
                        ('INFO', 'Information'),
                        ('WARNING', 'Avertissement'),
                        ('CRITICAL', 'Critique'),
                    ],
                    default='INFO',
                    max_length=10,
                    verbose_name='Sévérité',
                )),
                ('titre', models.CharField(max_length=255, verbose_name='Titre')),
                ('description', models.TextField(help_text='Explication IA détaillée', verbose_name='Description')),
                ('donnees', models.JSONField(blank=True, default=dict, help_text='Documents concernés, montants, dates, etc.', verbose_name='Données')),
                ('lu', models.BooleanField(default=False, verbose_name='Lu')),
                ('traite', models.BooleanField(default=False, verbose_name='Traité')),
                ('date_expiration', models.DateTimeField(blank=True, help_text="Auto-archivage après cette date", null=True, verbose_name="Date d'expiration")),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Créé par',
                )),
                ('mandat', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='insights',
                    to='core.mandat',
                    verbose_name='Mandat',
                )),
                ('documents', models.ManyToManyField(
                    blank=True,
                    related_name='insights',
                    to='documents.document',
                    verbose_name='Documents liés',
                )),
            ],
            options={
                'verbose_name': 'Insight de mandat',
                'verbose_name_plural': 'Insights de mandat',
                'db_table': 'mandat_insights',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mandatinsight',
            index=models.Index(fields=['mandat', 'type_insight'], name='mandat_insi_mandat__f0d09e_idx'),
        ),
        migrations.AddIndex(
            model_name='mandatinsight',
            index=models.Index(fields=['severite'], name='mandat_insi_severit_7384a6_idx'),
        ),
        migrations.AddIndex(
            model_name='mandatinsight',
            index=models.Index(fields=['lu'], name='mandat_insi_lu_59235a_idx'),
        ),
        migrations.AddIndex(
            model_name='mandatinsight',
            index=models.Index(fields=['traite'], name='mandat_insi_traite_73905d_idx'),
        ),

        # === MandatDigest ===
        migrations.CreateModel(
            name='MandatDigest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifié le')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
                ('type_digest', models.CharField(
                    choices=[
                        ('HEBDOMADAIRE', 'Hebdomadaire'),
                        ('MENSUEL', 'Mensuel'),
                        ('TRIMESTRIEL', 'Trimestriel'),
                    ],
                    max_length=15,
                    verbose_name='Type de digest',
                )),
                ('periode_debut', models.DateField(verbose_name='Début de période')),
                ('periode_fin', models.DateField(verbose_name='Fin de période')),
                ('resume', models.TextField(help_text='Résumé IA de la période', verbose_name='Résumé')),
                ('points_cles', models.JSONField(blank=True, default=list, help_text='Liste de faits saillants', verbose_name='Points clés')),
                ('statistiques', models.JSONField(blank=True, default=dict, help_text='Nombre de documents, montants, anomalies, etc.', verbose_name='Statistiques')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Créé par',
                )),
                ('mandat', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='digests',
                    to='core.mandat',
                    verbose_name='Mandat',
                )),
                ('insights_periode', models.ManyToManyField(
                    blank=True,
                    related_name='digests',
                    to='documents.mandatinsight',
                    verbose_name='Insights de la période',
                )),
                ('documents_periode', models.ManyToManyField(
                    blank=True,
                    related_name='digests',
                    to='documents.document',
                    verbose_name='Documents de la période',
                )),
            ],
            options={
                'verbose_name': 'Digest de mandat',
                'verbose_name_plural': 'Digests de mandat',
                'db_table': 'mandat_digests',
                'ordering': ['-periode_fin'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='mandatdigest',
            unique_together={('mandat', 'type_digest', 'periode_debut')},
        ),

        # === DocumentRelation ===
        migrations.CreateModel(
            name='DocumentRelation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifié le')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
                ('type_relation', models.CharField(
                    choices=[
                        ('DOUBLON', 'Doublon potentiel'),
                        ('VERSION', 'Version successive'),
                        ('REFERENCE', 'Référence croisée'),
                        ('COMPLEMENT', 'Document complémentaire'),
                        ('CONTRADICTION', 'Contradiction détectée'),
                        ('REPONSE', 'Réponse à'),
                    ],
                    max_length=20,
                    verbose_name='Type de relation',
                )),
                ('score_similarite', models.DecimalField(
                    decimal_places=3,
                    help_text='Score cosinus entre 0 et 1',
                    max_digits=4,
                    verbose_name='Score de similarité',
                )),
                ('description', models.TextField(
                    blank=True,
                    help_text='Explication IA de la relation',
                    verbose_name='Description',
                )),
                ('confirmee', models.BooleanField(
                    default=False,
                    help_text='Validation humaine de la relation',
                    verbose_name='Confirmée',
                )),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Métadonnées')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Créé par',
                )),
                ('document_source', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='relations_sortantes',
                    to='documents.document',
                    verbose_name='Document source',
                )),
                ('document_cible', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='relations_entrantes',
                    to='documents.document',
                    verbose_name='Document cible',
                )),
            ],
            options={
                'verbose_name': 'Relation de document',
                'verbose_name_plural': 'Relations de documents',
                'db_table': 'document_relations',
            },
        ),
        migrations.AlterUniqueTogether(
            name='documentrelation',
            unique_together={('document_source', 'document_cible', 'type_relation')},
        ),
        migrations.AddIndex(
            model_name='documentrelation',
            index=models.Index(fields=['document_source', 'type_relation'], name='document_re_documen_42b6c9_idx'),
        ),
        migrations.AddIndex(
            model_name='documentrelation',
            index=models.Index(fields=['score_similarite'], name='document_re_score_s_a3f1e2_idx'),
        ),
    ]
