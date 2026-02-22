# fiscalite/migrations/0007_declarationfiscale_devise_not_null.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0006_populate_declarationfiscale_devise'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='declarationfiscale',
            name='devise',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_fiscales',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de la déclaration fiscale',
            ),
        ),
    ]
