from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_rename_montant_forfait_to_budget_prevu"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="avatars/",
                verbose_name="Photo de profil",
            ),
        ),
    ]
