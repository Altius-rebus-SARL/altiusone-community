# facturation/migrations/0005_facture_devise_not_null.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0004_populate_facture_devise'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facture',
            name='devise',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='factures',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de facturation',
            ),
        ),
    ]
