# Generated manually for the multi-level collaborator system

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0010_user_contact_lie_user_doit_changer_mot_de_passe_and_more'),
    ]

    operations = [
        # Phase 1.1: Add type_collaborateur field to User
        migrations.AddField(
            model_name='user',
            name='type_collaborateur',
            field=models.CharField(
                choices=[('EMPLOYE', 'Employé'), ('PRESTATAIRE', 'Prestataire')],
                db_index=True,
                default='EMPLOYE',
                help_text='Employé = salarié/interne, Prestataire = externe/contractor',
                max_length=15,
                verbose_name='Type de collaborateur',
            ),
        ),

        # Phase 1.3: Create CollaborateurFiduciaire model
        migrations.CreateModel(
            name='CollaborateurFiduciaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Actif')),
                ('role_sur_mandat', models.CharField(blank=True, help_text='Ex: Comptable externe, Réviseur, Conseiller fiscal', max_length=100, verbose_name='Rôle sur ce mandat')),
                ('date_debut', models.DateField(verbose_name='Date de début')),
                ('date_fin', models.DateField(blank=True, null=True, verbose_name='Date de fin')),
                ('taux_horaire', models.DecimalField(blank=True, decimal_places=2, help_text='Taux horaire pour ce mandat (si différent du taux global)', max_digits=10, null=True, verbose_name='Taux horaire spécifique')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('mandat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prestataires_affectes', to='core.mandat', verbose_name='Mandat')),
                ('utilisateur', models.ForeignKey(limit_choices_to={'type_collaborateur': 'PRESTATAIRE', 'type_utilisateur': 'STAFF'}, on_delete=django.db.models.deletion.CASCADE, related_name='affectations_mandats', to=settings.AUTH_USER_MODEL, verbose_name='Prestataire')),
            ],
            options={
                'verbose_name': 'Affectation prestataire',
                'verbose_name_plural': 'Affectations prestataires',
                'db_table': 'collaborateurs_fiduciaire',
            },
        ),

        # Constraints and indexes for CollaborateurFiduciaire
        migrations.AddConstraint(
            model_name='collaborateurfiduciaire',
            constraint=models.UniqueConstraint(fields=['utilisateur', 'mandat'], name='unique_collaborateur_mandat'),
        ),
        migrations.AddIndex(
            model_name='collaborateurfiduciaire',
            index=models.Index(fields=['utilisateur', 'is_active'], name='collab_fid_user_active_idx'),
        ),
        migrations.AddIndex(
            model_name='collaborateurfiduciaire',
            index=models.Index(fields=['mandat', 'is_active'], name='collab_fid_mandat_active_idx'),
        ),

        # Phase 5.1: Update TypeInvitation choices (alter field)
        migrations.AlterField(
            model_name='invitation',
            name='type_invitation',
            field=models.CharField(
                choices=[
                    ('STAFF', 'Collaborateur interne'),
                    ('STAFF_PRESTATAIRE', 'Prestataire fiduciaire'),
                    ('CLIENT', 'Client externe'),
                    ('CLIENT_PRESTATAIRE', 'Prestataire client'),
                ],
                max_length=20,
                verbose_name="Type d'invitation",
            ),
        ),

        # Phase 5.2: Add mandats_assignes M2M field to Invitation
        migrations.AddField(
            model_name='invitation',
            name='mandats_assignes',
            field=models.ManyToManyField(
                blank=True,
                help_text='Mandats auxquels le prestataire sera affecté',
                related_name='invitations_prestataires',
                to='core.mandat',
                verbose_name='Mandats assignés',
            ),
        ),
    ]
