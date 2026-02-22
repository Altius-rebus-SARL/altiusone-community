# core/migrations/0004_tiers.py
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_comptebancaire_devise'),
        ('comptabilite', '0003_alter_ecriturecomptable_devise'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tiers',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(default=True, db_index=True, verbose_name='Actif')),
                ('code', models.CharField(db_index=True, max_length=50, verbose_name='Code')),
                ('nom', models.CharField(max_length=255, verbose_name='Nom')),
                ('type_tiers', models.CharField(choices=[('FOURNISSEUR', 'Fournisseur'), ('CLIENT', 'Client'), ('EMPLOYE', 'Employé'), ('ADMINISTRATION', 'Administration'), ('ASSOCIE', 'Associé'), ('AUTRE', 'Autre')], default='FOURNISSEUR', max_length=20, verbose_name='Type de tiers')),
                ('numero_tva', models.CharField(blank=True, max_length=50, verbose_name='Numéro TVA')),
                ('numero_ide', models.CharField(blank=True, max_length=20, verbose_name='Numéro IDE')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('telephone', models.CharField(blank=True, max_length=20, verbose_name='Téléphone')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('adresse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.adresse', verbose_name='Adresse')),
                ('client_lie', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.client', verbose_name='Client lié')),
                ('compte_associe', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='comptabilite.compte', verbose_name='Compte associé')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('devise', models.ForeignKey(default='CHF', on_delete=django.db.models.deletion.PROTECT, to='core.devise', verbose_name='Devise')),
                ('mandat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tiers', to='core.mandat', verbose_name='Mandat')),
            ],
            options={
                'verbose_name': 'Tiers',
                'verbose_name_plural': 'Tiers',
                'db_table': 'tiers',
                'ordering': ['nom'],
                'unique_together': {('mandat', 'code')},
            },
        ),
    ]
