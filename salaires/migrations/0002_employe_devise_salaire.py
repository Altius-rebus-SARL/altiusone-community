# salaires/migrations/0002_employe_devise_salaire.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0001_initial'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='employe',
            name='devise_salaire',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='employes',
                to='core.devise',
                verbose_name='Devise du salaire',
                help_text='Devise de versement du salaire',
            ),
        ),
    ]
