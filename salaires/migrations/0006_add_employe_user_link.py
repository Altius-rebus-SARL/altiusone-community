# Generated manually for the multi-level collaborator system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0005_employe_conjoint_travaille_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Phase 1.2: Add utilisateur FK to Employe
        migrations.AddField(
            model_name='employe',
            name='utilisateur',
            field=models.OneToOneField(
                blank=True,
                help_text='Compte utilisateur lié (si accès application)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employe_record',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Compte utilisateur',
            ),
        ),
    ]
