# salaires/migrations/0004_employe_devise_salaire_not_null.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0003_populate_employe_devise_salaire'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employe',
            name='devise_salaire',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='employes',
                to='core.devise',
                verbose_name='Devise du salaire',
                help_text='Devise de versement du salaire',
            ),
        ),
    ]
