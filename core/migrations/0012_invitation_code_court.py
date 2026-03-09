from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_tache_remove_assigne_a'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='code_court',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Code court à partager (ex: AB3K7X)",
                max_length=8,
                null=True,
                unique=True,
                verbose_name="Code d'invitation",
            ),
        ),
        migrations.AddIndex(
            model_name='invitation',
            index=models.Index(fields=['code_court'], name='invitations_code_co_idx'),
        ),
    ]
