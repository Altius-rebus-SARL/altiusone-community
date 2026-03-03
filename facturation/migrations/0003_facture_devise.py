# facturation/migrations/0003_facture_devise.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0002_alter_paiement_devise_alter_tarifmandat_devise'),
        ('core', '0005_mandat_regime_devise_client_regime'),
    ]

    operations = [
        migrations.AddField(
            model_name='facture',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='factures',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de facturation',
            ),
        ),
    ]
