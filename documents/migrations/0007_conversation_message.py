# Generated for AltiusOne Chat module
from django.db import migrations, models
from django.conf import settings
import uuid


class Migration(migrations.Migration):
    """
    Migration pour les modeles de chat documentaire.

    Cree les tables:
    - conversations: Conversations avec l'assistant AI
    - messages: Messages dans les conversations
    - messages_documents_contexte: Table de liaison M2M

    Ces tables permettent:
    - Chat avec contexte documentaire (mandat/document)
    - Historique des conversations
    - Tracking des tokens et performance
    - Feedback utilisateur sur les reponses
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0006_alter_embedding_dimensions_768'),
        ('core', '0007_alter_auditlog_action'),
    ]

    operations = [
        # 1. Creer la table conversations
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de creation')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('titre', models.CharField(blank=True, help_text='Titre genere automatiquement ou defini par utilisateur', max_length=255)),
                ('description', models.TextField(blank=True)),
                ('modele_ia', models.CharField(default='altiusone-chat', help_text='Modele AI utilise', max_length=50)),
                ('temperature', models.DecimalField(decimal_places=2, default=0.7, help_text='Temperature pour generation (0-1)', max_digits=3)),
                ('contexte_systeme', models.TextField(blank=True, help_text='Instructions systeme personnalisees')),
                ('statut', models.CharField(
                    choices=[
                        ('ACTIVE', 'Active'),
                        ('ARCHIVEE', 'Archivee'),
                        ('SUPPRIMEE', 'Supprimee')
                    ],
                    db_index=True,
                    default='ACTIVE',
                    max_length=20
                )),
                ('nombre_messages', models.IntegerField(default=0)),
                ('tokens_utilises', models.IntegerField(default=0)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=models.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Cree par'
                )),
                ('document', models.ForeignKey(
                    blank=True,
                    help_text='Document specifique pour le contexte',
                    null=True,
                    on_delete=models.SET_NULL,
                    related_name='conversations',
                    to='documents.document'
                )),
                ('mandat', models.ForeignKey(
                    blank=True,
                    help_text='Mandat pour contexte documentaire',
                    null=True,
                    on_delete=models.CASCADE,
                    related_name='conversations',
                    to='core.mandat'
                )),
                ('utilisateur', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='conversations',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Conversation',
                'verbose_name_plural': 'Conversations',
                'db_table': 'conversations',
                'ordering': ['-updated_at'],
            },
        ),

        # 2. Creer la table messages
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de creation')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('role', models.CharField(
                    choices=[
                        ('USER', 'Utilisateur'),
                        ('ASSISTANT', 'Assistant'),
                        ('SYSTEM', 'Systeme')
                    ],
                    db_index=True,
                    max_length=20
                )),
                ('contenu', models.TextField()),
                ('tokens_prompt', models.IntegerField(default=0, help_text='Tokens utilises pour le prompt')),
                ('tokens_completion', models.IntegerField(default=0, help_text='Tokens generes en reponse')),
                ('duree_ms', models.IntegerField(blank=True, help_text='Duree de generation en millisecondes', null=True)),
                ('sources', models.JSONField(blank=True, default=list, help_text="Sources citees par l'assistant")),
                ('feedback', models.CharField(
                    blank=True,
                    choices=[
                        ('POSITIF', 'Positif'),
                        ('NEGATIF', 'Negatif')
                    ],
                    max_length=20,
                    null=True
                )),
                ('commentaire_feedback', models.TextField(blank=True)),
                ('conversation', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='messages',
                    to='documents.conversation'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=models.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Cree par'
                )),
                ('documents_contexte', models.ManyToManyField(
                    blank=True,
                    help_text='Documents utilises comme contexte pour ce message',
                    related_name='messages_contexte',
                    to='documents.document'
                )),
            ],
            options={
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
                'db_table': 'messages',
                'ordering': ['created_at'],
            },
        ),

        # 3. Creer les index
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['utilisateur', 'statut'], name='conv_user_statut_idx'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['mandat', 'statut'], name='conv_mandat_statut_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'created_at'], name='msg_conv_created_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['role'], name='msg_role_idx'),
        ),
    ]
