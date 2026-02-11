# apps/modelforms/migrations/0003_public_access_and_mandats.py
import uuid

from django.conf import settings
from django.db import migrations, models


def populate_unique_tokens(apps, schema_editor):
    """Assign a unique UUID to each existing FormConfiguration."""
    FormConfiguration = apps.get_model('modelforms', 'FormConfiguration')
    for config in FormConfiguration.objects.all():
        config.public_token = uuid.uuid4()
        config.save(update_fields=['public_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('modelforms', '0002_multi_model_support'),
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Add public_token WITHOUT unique constraint
        migrations.AddField(
            model_name='formconfiguration',
            name='public_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                verbose_name='Token public',
                help_text='Token unique pour l\'accès public au formulaire',
            ),
        ),

        # Step 2: Populate each existing row with a unique UUID
        migrations.RunPython(populate_unique_tokens, migrations.RunPython.noop),

        # Step 3: Now add the unique constraint
        migrations.AlterField(
            model_name='formconfiguration',
            name='public_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                verbose_name='Token public',
                help_text='Token unique pour l\'accès public au formulaire',
            ),
        ),

        migrations.AddField(
            model_name='formconfiguration',
            name='access_level',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('public', 'Public – accessible sans authentification'),
                    ('code', 'Code d\'accès – nécessite un code'),
                    ('authenticated', 'Authentifié – nécessite un compte'),
                ],
                default='authenticated',
                verbose_name='Niveau d\'accès',
            ),
        ),
        migrations.AddField(
            model_name='formconfiguration',
            name='access_code',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                verbose_name='Code d\'accès',
            ),
        ),
        migrations.AddField(
            model_name='formconfiguration',
            name='success_message',
            field=models.TextField(
                blank=True,
                default='Merci ! Votre formulaire a été soumis avec succès.',
                verbose_name='Message de succès',
            ),
        ),

        # Mandats M2M on FormConfiguration
        migrations.AddField(
            model_name='formconfiguration',
            name='mandats',
            field=models.ManyToManyField(
                to='core.Mandat',
                blank=True,
                related_name='form_configurations',
                verbose_name='Mandats associés',
            ),
        ),

        # Make submitted_by nullable on FormSubmission (for anonymous submissions)
        migrations.AlterField(
            model_name='formsubmission',
            name='submitted_by',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                null=True,
                blank=True,
                related_name='form_submissions',
                verbose_name='Soumis par',
            ),
        ),
    ]
