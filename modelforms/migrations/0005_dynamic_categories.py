# apps/modelforms/migrations/0005_dynamic_categories.py
"""
Allow custom categories: remove choices constraint and increase max_length.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modelforms', '0004_populate_field_metadata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formconfiguration',
            name='category',
            field=models.CharField(
                max_length=50,
                default='AUTRE',
                db_index=True,
                verbose_name='Catégorie',
                help_text='Catégorie du formulaire pour le regroupement (personnalisable)',
            ),
        ),
    ]
