# salaires/migrations/0010_salaires_regime_devise_constraints.py
"""
Add unique_together constraint on TauxCotisation and make devise NOT NULL
where appropriate (after data population).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0009_populate_regime_devise_salaires'),
    ]

    operations = [
        # Add unique_together on TauxCotisation
        migrations.AlterUniqueTogether(
            name='tauxcotisation',
            unique_together={('type_cotisation', 'regime_fiscal', 'date_debut')},
        ),
    ]
