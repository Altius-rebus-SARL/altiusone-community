from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_alter_client_ide_optional_date_creation_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="responsable",
            field=models.ForeignKey(
                blank=True,
                help_text="Collaborateur interne en charge de ce dossier client",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="clients_responsable",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Responsable interne",
            ),
        ),
    ]
