from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_remove_iban_regex_validator'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='totp_secret',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Secret TOTP chiffré pour l'authentification à deux facteurs",
                max_length=255,
                verbose_name='Secret TOTP (chiffré)',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='backup_codes',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Liste de codes de secours hashés pour la 2FA',
                verbose_name='Codes de secours (hashés)',
            ),
        ),
    ]
