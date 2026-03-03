import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0012_populate_typeprestation'),
    ]

    operations = [
        # 1. Remove old CharField
        migrations.RemoveField(
            model_name='prestation',
            name='type_prestation',
        ),
        # 2. Rename FK ref → type_prestation
        migrations.RenameField(
            model_name='prestation',
            old_name='type_prestation_ref',
            new_name='type_prestation',
        ),
        # 3. Make NOT NULL + fix related_name
        migrations.AlterField(
            model_name='prestation',
            name='type_prestation',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='prestations',
                to='facturation.typeprestation',
                verbose_name='Type de prestation',
                help_text='Catégorie de la prestation',
            ),
        ),
    ]
